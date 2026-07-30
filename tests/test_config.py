"""Tests for OpenClaw JSON5 and env rendering."""

from __future__ import annotations

from lib_config import DENIED_A2A_TOOLS, render_agent_env, render_openclaw_json
from lib_models import AgentSpec, StackSpec


def _stack() -> StackSpec:
    """Two-agent stack fixture."""
    a1 = AgentSpec(
        index=1,
        name="agent-1",
        host_port=18789,
        telegram_bot_token="tok-a",
        gateway_token="gw-a",
        bot_numeric_id="111",
    )
    a2 = AgentSpec(
        index=2,
        name="agent-2",
        host_port=18790,
        telegram_bot_token="tok-b",
        gateway_token="gw-b",
        bot_numeric_id="222",
    )
    return StackSpec(agents=(a1, a2), owner_telegram_id="999")


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


def test_env_example_uses_placeholders() -> None:
    """Committed env examples must not embed live tokens."""
    stack = _stack()
    text = render_agent_env(stack.agents[0], example=True)
    assert "tok-a" not in text
    assert "TELEGRAM_BOT_TOKEN=REPLACE_WITH_" in text
    assert "OPENCLAW_GATEWAY_TOKEN=REPLACE_WITH_" in text
