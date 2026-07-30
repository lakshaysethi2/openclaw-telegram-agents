"""Tests for OpenClaw JSON5 and env rendering."""

from __future__ import annotations

from lib_config import DENIED_A2A_TOOLS, render_agent_env, render_openclaw_json
from lib_models import AgentSpec, StackSpec


def _stack(*, deepseek: bool = False) -> StackSpec:
    """Two-agent stack fixture."""
    common = {
        "provider_name": "deepseek" if deepseek else "",
        "provider_api_key": "sk-test-deepseek" if deepseek else "",
        "model_primary": "deepseek/deepseek-v4-flash" if deepseek else "",
        "context_tokens": 128000 if deepseek else None,
    }
    a1 = AgentSpec(
        index=1,
        name="agent-1",
        host_port=18789,
        telegram_bot_token="tok-a",
        gateway_token="gw-a",
        bot_numeric_id="111",
        **common,
    )
    a2 = AgentSpec(
        index=2,
        name="agent-2",
        host_port=18790,
        telegram_bot_token="tok-b",
        gateway_token="gw-b",
        bot_numeric_id="222",
        **common,
    )
    return StackSpec(
        agents=(a1, a2),
        owner_telegram_id="999",
        llm_provider="deepseek" if deepseek else "",
    )


def test_openclaw_json_allowlist_peers_and_owner() -> None:
    """Agent-1 allowFrom must include owner and agent-2 bot id only."""
    stack = _stack()
    text = render_openclaw_json(stack, stack.agents[0])
    assert '"999"' in text
    assert '"222"' in text
    assert '"111"' not in text  # self bot id not required in own allowFrom
    assert 'dmPolicy: "allowlist"' in text
    assert "botToBot" not in text
    assert "allowBots" not in text
    assert "agents.entries" not in text
    assert "entries:" not in text


def test_openclaw_json_denies_internal_a2a_tools() -> None:
    """Internal multi-agent tools must be denied so Telegram stays the bus."""
    stack = _stack()
    text = render_openclaw_json(stack, stack.agents[1])
    for tool in DENIED_A2A_TOOLS:
        assert f'"{tool}"' in text


def test_openclaw_json_deepseek_model_and_context() -> None:
    """DeepSeek setup must set model primary and contextTokens."""
    stack = _stack(deepseek=True)
    text = render_openclaw_json(stack, stack.agents[0])
    assert 'primary: "deepseek/deepseek-v4-flash"' in text
    assert "contextTokens: 128000" in text
    assert "api.deepseek.com" in text
    assert "sk-test-deepseek" not in text  # never embed key in json


def test_env_example_uses_placeholders() -> None:
    """Committed env examples must not embed live tokens."""
    stack = _stack()
    text = render_agent_env(stack.agents[0], example=True)
    assert "tok-a" not in text
    assert "TELEGRAM_BOT_TOKEN=REPLACE_WITH_" in text
    assert "OPENCLAW_GATEWAY_TOKEN=REPLACE_WITH_" in text


def test_env_live_deepseek_key() -> None:
    """Live env for DeepSeek must include DEEPSEEK_API_KEY only in live file."""
    stack = _stack(deepseek=True)
    live = render_agent_env(stack.agents[0], example=False)
    example = render_agent_env(stack.agents[0], example=True)
    assert "DEEPSEEK_API_KEY=sk-test-deepseek" in live
    assert "sk-test-deepseek" not in example
    assert "DEEPSEEK_API_KEY=REPLACE_WITH_DEEPSEEK_API_KEY" in example
