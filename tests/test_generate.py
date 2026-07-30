"""End-to-end generator tests against a temporary directory."""

from __future__ import annotations

from pathlib import Path

from generate_stack import build_default_stack, write_stack_files
from setup_agents import prompt_stack


def test_write_stack_files_creates_two_agent_layout(tmp_path: Path) -> None:
    """Default two-agent generation creates expected paths."""
    stack = build_default_stack(agent_count=2, owner_telegram_id="12345")
    written = write_stack_files(stack, root=tmp_path, write_live_env=True)
    assert (tmp_path / "docker-compose.yml").is_file()
    assert (tmp_path / "agents" / "agent-1" / "state" / "openclaw.json").is_file()
    assert (tmp_path / "agents" / "agent-2" / "state" / "openclaw.json").is_file()
    assert (tmp_path / "agents" / "agent-1" / ".env").is_file()
    assert (tmp_path / "agents" / "agent-2" / ".env.example").is_file()
    assert len(written) >= 8


def test_prompt_stack_with_injected_input(monkeypatch: object) -> None:
    """Interactive setup can be driven without real stdin/Telegram."""
    answers = iter(["2", "424242", "111", "222"])
    secrets = iter(["111:AAA", "222:BBB"])

    def fake_input(prompt: str) -> str:  # noqa: ARG001
        return next(answers)

    def fake_password(prompt: str) -> str:  # noqa: ARG001
        return next(secrets)

    stack = prompt_stack(
        input_fn=fake_input,
        password_fn=fake_password,
        resolve_identities=False,
    )
    assert len(stack.agents) == 2
    assert stack.owner_telegram_id == "424242"
    assert stack.agents[0].telegram_bot_token == "111:AAA"
    assert stack.agents[1].host_port == 18790
