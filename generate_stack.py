#!/usr/bin/env python3
"""Non-interactive stack file generator.

Writes docker-compose.yml, agent dirs, env examples, openclaw.json, IDENTITY.md.

Example:
    python generate_stack.py --agents 2 --owner-id 123456789
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from lib_compose import render_compose
from lib_config import (
    render_agent_env,
    render_identity_md,
    render_openclaw_json,
    render_root_env_example,
)
from lib_logging import log_error, setup_logging
from lib_models import AgentSpec, StackSpec, ValidationError, parse_positive_int
from lib_paths import (
    agent_auth_dir,
    agent_dir,
    agent_env_example_path,
    agent_env_path,
    agent_slug,
    agent_state_dir,
    agent_workspace_dir,
    compose_path,
    openclaw_config_path,
    repo_root,
)


def build_default_stack(
    *,
    agent_count: int,
    owner_telegram_id: str,
    base_port: int = 18789,
    openclaw_image: str = "ghcr.io/openclaw/openclaw:latest",
    tokens: list[str] | None = None,
    bot_ids: list[str] | None = None,
    write_live_env: bool = False,
) -> StackSpec:
    """Build a StackSpec with placeholders or provided tokens/ids.

    Args:
        agent_count: Number of agents (>= 2).
        owner_telegram_id: Human numeric Telegram id or placeholder.
        base_port: Host port for agent-1.
        openclaw_image: Container image.
        tokens: Optional per-agent Telegram bot tokens.
        bot_ids: Optional per-agent numeric bot ids.
        write_live_env: Unused here; retained for call-site clarity.

    Returns:
        Validated StackSpec.
    """
    _ = write_live_env
    agents: list[AgentSpec] = []
    for i in range(1, agent_count + 1):
        name = agent_slug(i)
        token = (
            tokens[i - 1]
            if tokens and i - 1 < len(tokens)
            else f"REPLACE_WITH_{name.upper().replace('-', '_')}_TELEGRAM_BOT_TOKEN"
        )
        bot_id = (
            bot_ids[i - 1]
            if bot_ids and i - 1 < len(bot_ids)
            else f"REPLACE_WITH_{name.upper().replace('-', '_')}_BOT_NUMERIC_ID"
        )
        agents.append(
            AgentSpec(
                index=i,
                name=name,
                host_port=base_port + (i - 1),
                telegram_bot_token=token,
                gateway_token=secrets.token_urlsafe(24),
                bot_numeric_id=bot_id,
            )
        )
    return StackSpec(
        agents=tuple(agents),
        owner_telegram_id=owner_telegram_id,
        openclaw_image=openclaw_image,
        base_port=base_port,
    )


def write_stack_files(
    stack: StackSpec,
    *,
    root: Path | None = None,
    write_live_env: bool = False,
) -> list[Path]:
    """Materialize compose + agent filesystem layout.

    Args:
        stack: Stack to write.
        root: Repo root override (tests use tmp paths).
        write_live_env: When True, also write gitignored agents/*/.env.

    Returns:
        List of paths written.
    """
    base = root or repo_root()
    written: list[Path] = []

    compose = compose_path(base)
    compose.write_text(render_compose(stack), encoding="utf-8")
    written.append(compose)

    root_example = base / ".env.example"
    root_example.write_text(render_root_env_example(stack), encoding="utf-8")
    written.append(root_example)

    root_env = base / ".env"
    if not root_env.exists():
        root_env.write_text(f"OPENCLAW_IMAGE={stack.openclaw_image}\n", encoding="utf-8")
        written.append(root_env)

    for agent in stack.agents:
        for directory in (
            agent_dir(agent.name, base),
            agent_state_dir(agent.name, base),
            agent_workspace_dir(agent.name, base),
            agent_auth_dir(agent.name, base),
        ):
            directory.mkdir(parents=True, exist_ok=True)

        (agent_auth_dir(agent.name, base) / ".gitkeep").write_text("", encoding="utf-8")
        cfg = openclaw_config_path(agent.name, base)
        cfg.write_text(render_openclaw_json(stack, agent), encoding="utf-8")
        written.append(cfg)

        identity = agent_workspace_dir(agent.name, base) / "IDENTITY.md"
        identity.write_text(render_identity_md(agent, stack), encoding="utf-8")
        written.append(identity)

        env_example = agent_env_example_path(agent.name, base)
        env_example.write_text(render_agent_env(agent, example=True), encoding="utf-8")
        written.append(env_example)

        if write_live_env:
            env_live = agent_env_path(agent.name, base)
            env_live.write_text(render_agent_env(agent, example=False), encoding="utf-8")
            written.append(env_live)

    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for non-interactive generation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", default="2", help="Agent count (min 2).")
    parser.add_argument(
        "--owner-id",
        default="OWNER_TELEGRAM_ID",
        help="Human Telegram numeric user id (or placeholder).",
    )
    parser.add_argument("--base-port", default="18789", help="Host port for agent-1.")
    parser.add_argument(
        "--image",
        default="ghcr.io/openclaw/openclaw:latest",
        help="OpenClaw container image.",
    )
    parser.add_argument(
        "--write-live-env",
        action="store_true",
        help="Also write agents/*/.env (gitignored).",
    )
    parser.add_argument("--root", default="", help="Optional output root (tests).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code."""
    logger = setup_logging()
    args = parse_args(argv)
    try:
        count = parse_positive_int(args.agents, field_name="agents", minimum=2)
        base_port = parse_positive_int(args.base_port, field_name="base-port", minimum=1)
        stack = build_default_stack(
            agent_count=count,
            owner_telegram_id=str(args.owner_id).strip() or "OWNER_TELEGRAM_ID",
            base_port=base_port,
            openclaw_image=args.image,
            write_live_env=bool(args.write_live_env),
        )
        root = Path(args.root).resolve() if args.root else None
        written = write_stack_files(stack, root=root, write_live_env=bool(args.write_live_env))
        logger.info(
            "Stack files written",
            extra={
                "extra_fields": {
                    "files_written": len(written),
                    "stack": stack.to_public_dict(),
                }
            },
        )
        print(f"Wrote {len(written)} files for {len(stack.agents)} agents.")
        return 0
    except ValidationError as exc:
        log_error(
            logger,
            str(exc),
            code=exc.code,
            hint=exc.hint,
        )
        return 2
    except OSError as exc:
        log_error(
            logger,
            f"Filesystem error while writing stack: {exc}",
            code="FS_WRITE_FAILED",
            hint="Check directory permissions and disk space, then retry.",
            context={"errno": getattr(exc, "errno", None)},
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
