"""Tests for docker-compose generation isolation guarantees."""

from __future__ import annotations

from lib_compose import render_compose
from lib_models import AgentSpec, StackSpec


def _stack(n: int = 2) -> StackSpec:
    """Create an n-agent stack for compose rendering tests."""
    agents = tuple(
        AgentSpec(
            index=i,
            name=f"agent-{i}",
            host_port=18788 + i,
            telegram_bot_token="t",
            gateway_token="g",
            bot_numeric_id=str(i),
        )
        for i in range(1, n + 1)
    )
    return StackSpec(agents=agents, owner_telegram_id="1")


def test_compose_has_separate_networks_and_ports() -> None:
    """Each agent must have a unique host port and dedicated network."""
    text = render_compose(_stack(3))
    assert "  agent-1:" in text
    assert "  agent-2:" in text
    assert "  agent-3:" in text
    assert '"18789:18789"' in text
    assert '"18790:18789"' in text
    assert '"18791:18789"' in text
    assert "openclaw-agent-1-net" in text
    assert "openclaw-agent-2-net" in text
    assert "openclaw-agent-3-net" in text
    # services/networks must be mappings (keys indented under the section).
    assert text.index("services:") < text.index("  agent-1:")


def test_compose_forbids_shared_network_name() -> None:
    """Generator must not introduce a single shared network for all agents."""
    text = render_compose(_stack(2))
    assert "networks:\n    shared" not in text
    assert "network_mode:" not in text
    # Each service lists exactly one network entry name pattern.
    assert "agent_1_net" in text
    assert "agent_2_net" in text


def test_compose_has_no_docker_socket() -> None:
    """Hard security invariant: never mount the Docker socket."""
    text = render_compose(_stack(2))
    assert "/var/run/docker.sock" not in text
    assert "network_mode: host" not in text
