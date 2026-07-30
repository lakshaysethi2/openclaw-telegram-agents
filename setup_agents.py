#!/usr/bin/env python3
"""Interactive first-run setup for N isolated OpenClaw Telegram agents.

Prompts for:
  - agent count (minimum 2)
  - human owner Telegram numeric user id
  - one Telegram bot token per agent

Optionally calls Telegram getMe (via dockerized curl) to resolve bot numeric ids
and usernames. Never prints full bot tokens.
"""

from __future__ import annotations

import getpass
import json
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

from generate_stack import write_stack_files
from lib_logging import log_error, setup_logging
from lib_models import (
    AgentSpec,
    StackSpec,
    ValidationError,
    parse_positive_int,
    require_non_empty,
    require_numeric_id,
)
from lib_paths import agent_slug, repo_root

PromptFn = Callable[[str], str]
PasswordFn = Callable[[str], str]


def _mask_token(token: str) -> str:
    """Return a short masked token preview for logs/UI."""
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def fetch_bot_identity(token: str, timeout_sec: float = 15.0) -> tuple[str, str]:
    """Call Telegram getMe and return (numeric_id, username).

    Args:
        token: BotFather token (not logged).
        timeout_sec: HTTP timeout.

    Returns:
        Tuple of (bot_id, username_without_at).

    Raises:
        ValidationError: On HTTP/API/parse failures.
    """
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ValidationError(
            f"Telegram getMe HTTP {exc.code}.",
            code="TELEGRAM_GETME_HTTP",
            hint=(
                "Token may be invalid, or Telegram API is unreachable. "
                "Recheck the BotFather token and network egress."
            ),
        ) from exc
    except urllib.error.URLError as exc:
        raise ValidationError(
            f"Telegram getMe network error: {exc.reason!r}.",
            code="TELEGRAM_GETME_NETWORK",
            hint="Check internet connectivity and DNS, then retry setup.",
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "Telegram getMe returned non-JSON.",
            code="TELEGRAM_GETME_BAD_JSON",
            hint="Retry later; if persistent, inspect with curl in docker.",
        ) from exc

    if not payload.get("ok"):
        desc = payload.get("description", "unknown error")
        raise ValidationError(
            f"Telegram getMe ok=false: {desc}",
            code="TELEGRAM_GETME_NOT_OK",
            hint="Verify the bot token in BotFather and retry.",
        )

    result = payload.get("result") or {}
    bot_id = str(result.get("id", "")).strip()
    username = str(result.get("username", "")).strip().lstrip("@")
    if not bot_id.isdigit():
        raise ValidationError(
            "Telegram getMe missing numeric result.id.",
            code="TELEGRAM_GETME_NO_ID",
            hint="Unexpected API payload; re-run with a fresh bot token.",
        )
    return bot_id, username


def prompt_stack(
    *,
    input_fn: PromptFn = input,
    password_fn: PasswordFn = getpass.getpass,
    resolve_identities: bool = True,
) -> StackSpec:
    """Run interactive prompts and build a StackSpec.

    Args:
        input_fn: Injectable input for tests.
        password_fn: Injectable secret input for tests.
        resolve_identities: When True, call getMe for each token.

    Returns:
        Validated StackSpec ready to write.
    """
    print("OpenClaw multi-agent Telegram setup")
    print("Telegram is the only agent <-> agent path.\n")

    count_raw = input_fn("How many agents do you want to set up? [min 2]: ").strip()
    count = parse_positive_int(count_raw or "2", field_name="agent_count", minimum=2)

    owner_raw = input_fn("Authorized human Telegram numeric user id (not @username): ").strip()
    owner_id = require_numeric_id(owner_raw, field_name="owner_telegram_id")

    agents: list[AgentSpec] = []
    for i in range(1, count + 1):
        name = agent_slug(i)
        print(f"\n--- {name} ---")
        token = password_fn(f"Telegram bot token for {name} (input hidden): ").strip()
        token = require_non_empty(token, field_name=f"{name}.telegram_bot_token")

        bot_id = f"REPLACE_WITH_{name.upper().replace('-', '_')}_BOT_NUMERIC_ID"
        username = ""
        if resolve_identities:
            try:
                bot_id, username = fetch_bot_identity(token)
                print(f"  getMe ok: id={bot_id} username=@{username or 'unknown'}")
            except ValidationError as exc:
                print(f"  WARNING: getMe failed ({exc.code}): {exc}")
                print(f"  hint: {exc.hint}")
                manual = input_fn(
                    f"  Enter numeric bot id for {name} manually (or leave placeholder): "
                ).strip()
                if manual:
                    bot_id = require_numeric_id(manual, field_name=f"{name}.bot_id")

        gateway = secrets.token_urlsafe(24)
        agents.append(
            AgentSpec(
                index=i,
                name=name,
                host_port=18789 + (i - 1),
                telegram_bot_token=token,
                gateway_token=gateway,
                bot_numeric_id=bot_id,
                bot_username=username,
            )
        )
        print(f"  token accepted (masked): {_mask_token(token)}")

    return StackSpec(agents=tuple(agents), owner_telegram_id=owner_id)


def chown_agent_trees() -> None:
    """Best-effort chown to uid 1000 for OpenClaw node user bind mounts."""
    root = repo_root() / "agents"
    if not root.exists():
        return
    cmd = ["chown", "-R", "1000:1000", str(root)]
    try:
        subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError:
        # Non-fatal on hosts without permission; document in printed next steps.
        return


def main() -> int:
    """Interactive setup entrypoint."""
    logger = setup_logging()
    try:
        stack = prompt_stack()
        written = write_stack_files(stack, write_live_env=True)
        chown_agent_trees()
        logger.info(
            "Interactive setup complete",
            extra={"extra_fields": {"stack": stack.to_public_dict(), "files": len(written)}},
        )
        print("\nSetup complete.")
        print(f"Wrote {len(written)} files under {repo_root()}")
        print("\nNext steps:")
        print("  1) Enable Bot-to-Bot Communication for every bot in BotFather.")
        print("  2) make up")
        print("  3) make health")
        print("  4) make test-a2a FROM=agent-1 TO_USER=agent_2_username")
        print("  5) make logs SERVICE=agent-2")
        print("\nNever commit agents/*/.env files.")
        return 0
    except ValidationError as exc:
        log_error(logger, str(exc), code=exc.code, hint=exc.hint)
        print(f"ERROR [{exc.code}]: {exc}\nHINT: {exc.hint}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        log_error(
            logger,
            "Setup cancelled by user.",
            code="SETUP_CANCELLED",
            hint="Re-run: make setup  OR  python setup_agents.py",
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
