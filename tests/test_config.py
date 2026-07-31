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
    """Cross-agent bus tools stay denied; own-session visibility is agent-wide."""
    stack = _stack()
    text = render_openclaw_json(stack, stack.agents[1])
    for tool in DENIED_A2A_TOOLS:
        assert f'"{tool}"' in text
    assert 'visibility: "agent"' in text
    assert "agentToAgent" in text
    assert "enabled: false" in text
    # Same-agent recall tools must NOT be blanket-denied.
    assert '"sessions_list"' not in text.split("deny:", 1)[1]
    assert '"sessions_history"' not in text.split("deny:", 1)[1]
    assert '"sessions_send"' not in text.split("deny:", 1)[1]
    assert '"sessions_spawn"' not in text.split("deny:", 1)[1]


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


def test_discord_friend_bot_channel_render() -> None:
    """Discord-primary agent gets discord block and env token slot."""
    a1 = AgentSpec(
        index=1,
        name="agent-1",
        host_port=18791,
        telegram_bot_token="tok-a",
        gateway_token="gw-a",
        bot_numeric_id="111",
    )
    a3 = AgentSpec(
        index=3,
        name="agent-3",
        host_port=18793,
        telegram_bot_token="REPLACE_WITH_AGENT_3_TELEGRAM_BOT_TOKEN",
        gateway_token="gw-c",
        bot_numeric_id="333",
        channels=("discord", "telegram"),
        discord_bot_token="REPLACE_WITH_AGENT_3_DISCORD_BOT_TOKEN",
        discord_guild_id="123456789012345678",
        persona="Friend Bot",
    )
    stack = StackSpec(agents=(a1, a3), owner_telegram_id="999")
    text = render_openclaw_json(stack, a3)
    assert "discord:" in text
    assert "DISCORD_BOT_TOKEN" in text
    assert '"123456789012345678"' in text
    assert "telegram:" in text
    assert "enabled: false" in text  # telegram placeholder => disabled
    env = render_agent_env(a3, example=True)
    assert "DISCORD_BOT_TOKEN=REPLACE_WITH_AGENT_3_DISCORD_BOT_TOKEN" in env
    assert "TELEGRAM_BOT_TOKEN=REPLACE_WITH_AGENT_3_TELEGRAM_BOT_TOKEN" in env
