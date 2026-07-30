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
PUBLIC_JSON="${ROOT_DIR}/agents/stack-public.json"

print_known_commands() {
  if [[ -f "${PUBLIC_JSON}" ]]; then
    docker run --rm -v "${ROOT_DIR}:/app" -w /app python:3.11-slim \
      python - <<'PY'
import json
from pathlib import Path
path = Path("agents/stack-public.json")
data = json.loads(path.read_text(encoding="utf-8"))
cmds = data.get("test_a2a_commands") or []
agents = data.get("agents") or []
print("Known agents (from setup getMe / stack-public.json):")
for a in agents:
    uname = a.get("bot_username") or "(no username)"
    print(f"  - {a.get('name')}: @{uname} id={a.get('bot_numeric_id')}")
if cmds:
    print("Copy-paste tests:")
    for c in cmds:
        print(f"  {c}")
else:
    print("No bot usernames stored. Re-run: make setup")
PY
  else:
    echo "No agents/stack-public.json yet. Re-run: make setup" >&2
    echo "Usage: $0 <from_service> <to_bot_username>" >&2
  fi
}

resolve_to_user() {
  # When TO_USER is empty, pick the only other agent username if possible.
  if [[ -n "${RAW_USERNAME}" ]]; then
    return 0
  fi
  if [[ ! -f "${PUBLIC_JSON}" ]]; then
    echo "ERROR: TO_USER not set and agents/stack-public.json missing." >&2
    print_known_commands
    exit 2
  fi
  RAW_USERNAME="$(
    docker run --rm -v "${ROOT_DIR}:/app" -w /app -e FROM_SERVICE="${FROM_SERVICE}" \
      python:3.11-slim python - <<'PY'
import json, os
from pathlib import Path
from_name = os.environ["FROM_SERVICE"]
data = json.loads(Path("agents/stack-public.json").read_text(encoding="utf-8"))
peers = [
    a for a in data.get("agents") or []
    if a.get("name") != from_name and a.get("bot_username")
]
if len(peers) == 1:
    print(peers[0]["bot_username"])
elif len(peers) == 0:
    raise SystemExit(0)
else:
    raise SystemExit(0)
PY
  )"
  if [[ -z "${RAW_USERNAME}" ]]; then
    echo "ERROR: TO_USER not set and could not auto-pick a single peer." >&2
    print_known_commands
    exit 2
  fi
  echo "Auto-selected TO_USER=${RAW_USERNAME} (from agents/stack-public.json)"
}

resolve_to_user

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

TARGET_SERVICE=""
if [[ -f "${PUBLIC_JSON}" ]]; then
  TARGET_SERVICE="$(
    docker run --rm -v "${ROOT_DIR}:/app" -w /app -e TO_USER="${USERNAME_NO_AT}" \
      python:3.11-slim python - <<'PY'
import json, os
from pathlib import Path
want = os.environ["TO_USER"].lstrip("@").lower()
data = json.loads(Path("agents/stack-public.json").read_text(encoding="utf-8"))
for a in data.get("agents") or []:
    if str(a.get("bot_username") or "").lstrip("@").lower() == want:
        print(a.get("name") or "")
        break
PY
  )"
fi

cat <<EOF
RESULT: stage 1 OK (Telegram accepted sendMessage).
Next stages (manual):
  2) OpenClaw inbound on target: make logs SERVICE=${TARGET_SERVICE:-agent-2}
  3) Model turn (needs provider key + make enable-deepseek on target)
  4) Target reply message (e.g. A2A_ACK)
Do not widen allowlists to wildcards if stage 1 passes but later stages fail.
EOF
