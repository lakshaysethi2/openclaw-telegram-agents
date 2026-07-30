#!/usr/bin/env bash
# Manual Telegram transport test: FROM agent bot -> TO bot username.
# Not run during compose up. Never prints bot tokens. Never calls getUpdates.
#
# Usage:
#   ./test_a2a.sh <from_service> <to_bot_username>
#   make test-a2a FROM=agent-1 TO_USER=my_agent2_bot
#   make test-a2a FROM=agent-1   # auto-pick peer from agents/stack-public.json
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

FROM_SERVICE="${1:-${FROM:-agent-1}}"
RAW_USERNAME="${2:-${TO_USER:-}}"

py_public() {
  docker run --rm -v "${ROOT_DIR}:/app" -w /app python:3.11-slim \
    python lib_stack_public.py "$@"
}

if [[ -z "${RAW_USERNAME}" ]]; then
  RAW_USERNAME="$(py_public peer "${FROM_SERVICE}" | tr -d '\r' | tail -n 1)"
  if [[ -z "${RAW_USERNAME}" ]]; then
    echo "ERROR: TO_USER not set and could not auto-pick a single peer." >&2
    py_public list
    exit 2
  fi
  echo "Auto-selected TO_USER=${RAW_USERNAME} (from agents/stack-public.json)"
fi

USERNAME_NO_AT="${RAW_USERNAME#@}"
CHAT_ID="@${USERNAME_NO_AT}"

echo "== A2A transport test =="
echo "from_service=${FROM_SERVICE} chat_id=${CHAT_ID}"

need_running() {
  local service="$1"
  if ! docker compose ps --status running --services 2>/dev/null | grep -qx "$service"; then
    echo "ERROR: service '${service}' is not running. Run: make up" >&2
    exit 1
  fi
  echo "OK: ${service} running"
}

need_running "${FROM_SERVICE}"

TOKEN="$(docker compose exec -T "${FROM_SERVICE}" printenv TELEGRAM_BOT_TOKEN 2>/dev/null || true)"
if [[ -z "${TOKEN}" && -f "agents/${FROM_SERVICE}/.env" ]]; then
  TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' "agents/${FROM_SERVICE}/.env" | head -1 | cut -d= -f2-)"
fi

if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: missing TELEGRAM_BOT_TOKEN for ${FROM_SERVICE}" >&2
  exit 1
fi
if [[ "${TOKEN}" == REPLACE_WITH_* || "${TOKEN}" == *PLACEHOLDER* ]]; then
  echo "ERROR: ${FROM_SERVICE} TELEGRAM_BOT_TOKEN is still a placeholder. Run: make setup" >&2
  exit 1
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RAND="$(printf '%04x' "$RANDOM")"
TEXT="A2A_BOOTSTRAP_TEST: reply exactly A2A_ACK [${TS}-${RAND}]"
echo "Sending text: ${TEXT}"

RESPONSE="$(
  docker run --rm curlimages/curl:8.12.1 \
    -sS -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${TEXT}"
)"
SAFE_RESPONSE="${RESPONSE//${TOKEN}/***REDACTED***}"
echo "Telegram API response:"
echo "${SAFE_RESPONSE}"

OK_FIELD="$(
  printf '%s' "${SAFE_RESPONSE}" | docker run --rm -i python:3.11-slim \
    python -c 'import sys,json
d=json.load(sys.stdin)
print("true" if d.get("ok") is True else "false")'
)"

if [[ "${OK_FIELD}" != "true" ]]; then
  echo "RESULT: Telegram transport FAILED (stage 1)."
  echo "Classify: bot-to-bot opt-in | bad username | bad token | API error"
  exit 1
fi

TARGET_SERVICE="$(py_public service "${USERNAME_NO_AT}" | tr -d '\r' | tail -n 1)"
if [[ -z "${TARGET_SERVICE}" ]]; then
  TARGET_SERVICE="agent-2"
fi

cat <<EOF
RESULT: stage 1 OK (Telegram accepted sendMessage).
Next stages (manual):
  2) OpenClaw inbound on target: make logs SERVICE=${TARGET_SERVICE}
  3) Model turn (needs provider key + make enable-deepseek on target)
  4) Target reply message (e.g. A2A_ACK)
Do not widen allowlists to wildcards if stage 1 passes but later stages fail.
EOF
