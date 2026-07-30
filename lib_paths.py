"""Filesystem path helpers for the multi-agent stack.

Keeps path conventions in one place so generators and tests stay consistent.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (directory containing this file)."""
    return Path(__file__).resolve().parent


def agents_root(root: Path | None = None) -> Path:
    """Return the ``agents/`` directory under the repo root."""
    base = root or repo_root()
    return base / "agents"


def agent_dir(name: str, root: Path | None = None) -> Path:
    """Return ``agents/<name>/`` for a given agent slug."""
    return agents_root(root) / name


def agent_state_dir(name: str, root: Path | None = None) -> Path:
    """Return the OpenClaw state bind-mount directory for an agent."""
    return agent_dir(name, root) / "state"


def agent_workspace_dir(name: str, root: Path | None = None) -> Path:
    """Return the workspace bind-mount directory for an agent."""
    return agent_dir(name, root) / "workspace"


def agent_auth_dir(name: str, root: Path | None = None) -> Path:
    """Return the auth-profile bind-mount directory for an agent."""
    return agent_dir(name, root) / "auth"


def agent_env_path(name: str, root: Path | None = None) -> Path:
    """Return the live ``.env`` path for an agent (gitignored)."""
    return agent_dir(name, root) / ".env"


def agent_env_example_path(name: str, root: Path | None = None) -> Path:
    """Return the committed ``.env.example`` path for an agent."""
    return agent_dir(name, root) / ".env.example"


def openclaw_config_path(name: str, root: Path | None = None) -> Path:
    """Return ``agents/<name>/state/openclaw.json``."""
    return agent_state_dir(name, root) / "openclaw.json"


def compose_path(root: Path | None = None) -> Path:
    """Return the generated ``docker-compose.yml`` path."""
    base = root or repo_root()
    return base / "docker-compose.yml"


def agent_slug(index: int) -> str:
    """Build the canonical agent directory/service name from a 1-based index."""
    if index < 1:
        raise ValueError(f"agent index must be >= 1, got {index}")
    return f"agent-{index}"
