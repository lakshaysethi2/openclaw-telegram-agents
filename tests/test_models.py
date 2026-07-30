"""Unit tests for typed stack models and input validation."""

from __future__ import annotations

import pytest

from lib_models import (
    AgentSpec,
    StackSpec,
    ValidationError,
    parse_context_tokens,
    parse_positive_int,
    parse_yes_no,
    require_numeric_id,
)


def _agent(index: int, port: int | None = None) -> AgentSpec:
    """Build a minimal agent fixture."""
    return AgentSpec(
        index=index,
        name=f"agent-{index}",
        host_port=port if port is not None else 18788 + index,
        telegram_bot_token=f"token-{index}",
        gateway_token=f"gateway-{index}",
        bot_numeric_id=str(1000 + index),
    )


def test_stack_requires_min_two_agents() -> None:
    """StackSpec must reject fewer than two agents."""
    with pytest.raises(ValidationError) as exc:
        StackSpec(agents=(_agent(1),), owner_telegram_id="1")
    assert exc.value.code == "STACK_MIN_AGENTS"


def test_peer_ids_include_owner_and_other_bots_only() -> None:
    """Each agent allowlist is owner + every other bot id (not self)."""
    stack = StackSpec(
        agents=(_agent(1), _agent(2), _agent(3)),
        owner_telegram_id="42",
    )
    peers = stack.peer_ids_for(stack.agents[0])
    assert peers == ["42", "1002", "1003"]


def test_parse_positive_int_minimum() -> None:
    """parse_positive_int enforces the configured minimum."""
    assert parse_positive_int("3", field_name="n", minimum=2) == 3
    with pytest.raises(ValidationError) as exc:
        parse_positive_int("1", field_name="n", minimum=2)
    assert exc.value.code == "INPUT_TOO_SMALL"


def test_require_numeric_id_accepts_negative_chat() -> None:
    """Group chat ids may start with '-'."""
    assert require_numeric_id("-100123", field_name="chat") == "-100123"


def test_require_numeric_id_rejects_username() -> None:
    """allowFrom must not receive @username strings."""
    with pytest.raises(ValidationError) as exc:
        require_numeric_id("@someone", field_name="owner")
    assert exc.value.code == "INPUT_NOT_NUMERIC_ID"


def test_public_dict_redacts_secrets() -> None:
    """to_public_dict must not leak tokens."""
    stack = StackSpec(agents=(_agent(1), _agent(2)), owner_telegram_id="9")
    public = stack.to_public_dict()
    blob = str(public)
    assert "token-1" not in blob
    assert "gateway-1" not in blob
    assert "***REDACTED***" in blob


def test_parse_context_tokens_bounds() -> None:
    """Context window must stay within safe runtime bounds."""
    assert parse_context_tokens("128000") == 128000
    with pytest.raises(ValidationError) as exc:
        parse_context_tokens("100")
    assert exc.value.code == "INPUT_TOO_SMALL"
    with pytest.raises(ValidationError) as exc2:
        parse_context_tokens("5000000")
    assert exc2.value.code == "CONTEXT_TOO_LARGE"


def test_parse_yes_no_defaults() -> None:
    """Empty yes/no answers use the provided default."""
    assert parse_yes_no("", default=True) is True
    assert parse_yes_no("n", default=True) is False
    assert parse_yes_no("YES", default=False) is True
