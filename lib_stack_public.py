"""Read non-secret stack-public.json helpers for operator scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from lib_paths import repo_root, stack_public_path


def load_stack_public(root: Path | None = None) -> dict[str, Any]:
    """Load agents/stack-public.json or return empty structure."""
    path = stack_public_path(root)
    if not path.is_file():
        return {"agents": [], "test_a2a_commands": []}
    return json.loads(path.read_text(encoding="utf-8"))


def peer_username(from_service: str, root: Path | None = None) -> str:
    """Return the only other agent username, or empty if ambiguous/missing."""
    data = load_stack_public(root)
    peers = [
        str(a.get("bot_username") or "").lstrip("@")
        for a in data.get("agents") or []
        if a.get("name") != from_service and a.get("bot_username")
    ]
    peers = [p for p in peers if p]
    if len(peers) == 1:
        return peers[0]
    return ""


def service_for_username(username: str, root: Path | None = None) -> str:
    """Map a bot username back to agent service name."""
    want = username.lstrip("@").lower()
    for agent in load_stack_public(root).get("agents") or []:
        have = str(agent.get("bot_username") or "").lstrip("@").lower()
        if have and have == want:
            return str(agent.get("name") or "")
    return ""


def print_known_commands(root: Path | None = None) -> None:
    """Print agents and copy-paste make test-a2a lines."""
    base = root or repo_root()
    path = stack_public_path(base)
    if not path.is_file():
        print("No agents/stack-public.json yet. Re-run: make setup", file=sys.stderr)
        print("Usage: make test-a2a FROM=agent-1 TO_USER=peer_bot_username", file=sys.stderr)
        return
    data = load_stack_public(base)
    print("Known agents (from setup getMe / stack-public.json):")
    for agent in data.get("agents") or []:
        uname = agent.get("bot_username") or "(no username)"
        print(f"  - {agent.get('name')}: @{uname} id={agent.get('bot_numeric_id')}")
    cmds = data.get("test_a2a_commands") or []
    if cmds:
        print("Copy-paste tests:")
        for cmd in cmds:
            print(f"  {cmd}")
    else:
        print("No bot usernames stored. Re-run: make setup")


def main(argv: list[str] | None = None) -> int:
    """Tiny CLI used by test_a2a.sh.

    Commands:
      list
      peer <from_service>
      service <bot_username>
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "list"}:
        print_known_commands()
        return 0
    if args[0] == "peer" and len(args) >= 2:
        print(peer_username(args[1]))
        return 0
    if args[0] == "service" and len(args) >= 2:
        print(service_for_username(args[1]))
        return 0
    print("Usage: lib_stack_public.py [list|peer FROM|service USERNAME]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
