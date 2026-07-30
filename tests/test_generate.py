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
    assert (tmp_path / "agents" / "stack-public.json").is_file()
    assert len(written) >= 8


def test_prompt_stack_with_deepseek(monkeypatch: object) -> None:
    """Interactive setup captures DeepSeek model + context for each agent."""
    _ = monkeypatch
    # order: count, owner, use deepseek Y, same settings Y, model default, context default,
    # agent1 persona, agent2 persona, write Y
    answers = iter(
        [
            "2",
            "424242",
            "y",  # use deepseek
            "y",  # same settings
            "",  # model default flash
            "64000",  # context
            "researcher",  # persona 1
            "writer",  # persona 2
            "y",  # write
        ]
    )
    secrets = iter(["sk-deepseek-test-key", "111:AAA", "222:BBB"])

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
    assert stack.llm_provider == "deepseek"
    assert stack.agents[0].telegram_bot_token == "111:AAA"
    assert stack.agents[0].provider_api_key == "sk-deepseek-test-key"
    assert stack.agents[0].model_primary == "deepseek/deepseek-v4-flash"
    assert stack.agents[0].context_tokens == 64000
    assert stack.agents[0].persona == "researcher"
    assert stack.agents[1].persona == "writer"
    assert stack.agents[1].host_port == 18790


def test_stack_public_includes_test_commands(tmp_path: Path) -> None:
    """stack-public.json must list copy-paste test-a2a commands with usernames."""
    import json

    from lib_models import AgentSpec, StackSpec

    a1 = AgentSpec(
        index=1,
        name="agent-1",
        host_port=18789,
        telegram_bot_token="t1",
        gateway_token="g1",
        bot_numeric_id="111",
        bot_username="bot_one",
    )
    a2 = AgentSpec(
        index=2,
        name="agent-2",
        host_port=18790,
        telegram_bot_token="t2",
        gateway_token="g2",
        bot_numeric_id="222",
        bot_username="bot_two",
    )
    stack = StackSpec(agents=(a1, a2), owner_telegram_id="9")
    write_stack_files(stack, root=tmp_path, write_live_env=False)
    data = json.loads((tmp_path / "agents" / "stack-public.json").read_text())
    assert "make test-a2a FROM=agent-1 TO_USER=bot_two" in data["test_a2a_commands"]
    assert "make test-a2a FROM=agent-2 TO_USER=bot_one" in data["test_a2a_commands"]
    assert "t1" not in json.dumps(data)


def test_prompt_stack_skip_llm() -> None:
    """Operators can skip DeepSeek and configure providers later."""
    answers = iter(
        [
            "2",
            "99",
            "n",  # skip deepseek
            "",  # persona 1
            "",  # persona 2
            "y",  # write
        ]
    )
    secrets = iter(["tok1", "tok2"])

    stack = prompt_stack(
        input_fn=lambda _p: next(answers),
        password_fn=lambda _p: next(secrets),
        resolve_identities=False,
    )
    assert stack.llm_provider == ""
    assert stack.agents[0].model_primary == ""
    assert stack.agents[0].provider_api_key == ""
