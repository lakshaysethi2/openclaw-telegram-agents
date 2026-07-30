#!/usr/bin/env python3
"""Interactive first-run setup for N isolated OpenClaw Telegram agents.

Prompts for agent count, owner Telegram id, bot tokens, optional DeepSeek
provider key, per-agent default model + context window, and optional persona.
Never prints full bot tokens or API keys.
"""

from __future__ import annotations

import getpass
import json
import secrets
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
from lib_setup import (
    mask_secret,
    print_setup_summary,
    prompt_llm_settings,
    prompt_persona,
    prompt_yes_no,
)

PromptFn = Callable[[str], str]
PasswordFn = Callable[[str], str]


def fetch_bot_identity(token: str, timeout_sec: float = 15.0) -> tuple[str, str]:
    """Call Telegram getMe and return (numeric_id, username)."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ValidationError(
            f"Telegram getMe HTTP {exc.code}.",
            code="TELEGRAM_GETME_HTTP",
            hint="Token may be invalid, or Telegram API is unreachable.",
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
    """Run interactive prompts and build a StackSpec."""
    print("OpenClaw multi-agent Telegram setup")
    print("Telegram is the only agent <-> agent path.\n")

    count_raw = input_fn("How many agents do you want to set up? [min 2]: ").strip()
    count = parse_positive_int(count_raw or "2", field_name="agent_count", minimum=2)

    print(
        "Authorized human Telegram numeric user id is required for DM allowlists."
    )
    print("  Tip: message @userinfobot or @getidsbot on Telegram to see your id.")
    owner_raw = input_fn("Your Telegram numeric user id (not @username): ").strip()
    owner_id = require_numeric_id(owner_raw, field_name="owner_telegram_id")

    provider, api_key, models, contexts = prompt_llm_settings(
        agent_count=count,
        input_fn=input_fn,
        password_fn=password_fn,
    )

    agents: list[AgentSpec] = []
    bot_labels: list[str] = []
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

        persona = prompt_persona(input_fn=input_fn, agent_name=name)
        model = models[i - 1] if i - 1 < len(models) else ""
        ctx_raw = contexts[i - 1] if i - 1 < len(contexts) else 0
        context_tokens = ctx_raw if ctx_raw and ctx_raw > 0 else None

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
                provider_api_key=api_key,
                provider_name=provider,
                model_primary=model,
                context_tokens=context_tokens,
                persona=persona,
            )
        )
        label = f"@{username}" if username else f"id={bot_id}"
        bot_labels.append(f"{label} token={mask_secret(token)}")
        print(f"  token accepted (masked): {mask_secret(token)}")

    print_setup_summary(
        agent_count=count,
        owner_id=owner_id,
        provider=provider,
        models=models,
        contexts=contexts,
        bot_labels=bot_labels,
    )
    if not prompt_yes_no("Write compose + agent files now?", default=True, input_fn=input_fn):
        raise ValidationError(
            "Setup cancelled before writing files.",
            code="SETUP_ABORTED",
            hint="Re-run: make setup",
        )

    return StackSpec(
        agents=tuple(agents),
        owner_telegram_id=owner_id,
        llm_provider=provider,
    )


def print_next_steps(stack: StackSpec) -> None:
    """Print operator next steps after a successful write."""
    print("\nSetup complete.")
    print(f"Wrote files under {repo_root()}")
    print("\nNext steps:")
    print("  1) In BotFather, enable Bot-to-Bot Communication for EVERY bot.")
    print("  2) make up")
    print("  3) make health")
    if stack.uses_deepseek():
        print("  4) make enable-deepseek   # install official DeepSeek plugin in each agent")
        print("  5) make test-a2a FROM=agent-1 TO_USER=<agent_2_bot_username>")
        print("  6) make logs SERVICE=agent-2")
    else:
        print("  4) Add a model provider key in agents/*/.env then restart: make restart")
        print("  5) make test-a2a FROM=agent-1 TO_USER=<agent_2_bot_username>")
    print("\nNever commit agents/*/.env files.")


def main() -> int:
    """Interactive setup entrypoint."""
    logger = setup_logging()
    try:
        stack = prompt_stack()
        written = write_stack_files(stack, write_live_env=True)
        logger.info(
            "Interactive setup complete",
            extra={"extra_fields": {"stack": stack.to_public_dict(), "files": len(written)}},
        )
        print(f"Wrote {len(written)} files.")
        print_next_steps(stack)
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
