"""Typed data models for multi-agent OpenClaw Telegram stacks.

All public structures used by generators and tests live here so maintainers
do not guess field names or types.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


class ValidationError(ValueError):
    """Raised when user input or generated config fails hard validation.

    Attributes:
        code: Stable error code for logs and tests.
        hint: Explicit recovery guidance for operators and AI maintainers.
    """

    def __init__(self, message: str, *, code: str, hint: str) -> None:
        super().__init__(message)
        self.code = code
        self.hint = hint


# Known DeepSeek model refs (OpenClaw provider docs, 2026.7).
DEEPSEEK_MODEL_CHOICES: tuple[tuple[str, str], ...] = (
    ("deepseek/deepseek-v4-flash", "Fast V4 (default; good cost/latency)"),
    ("deepseek/deepseek-v4-pro", "Stronger V4 (higher quality, higher cost)"),
)
DEEPSEEK_DEFAULT_MODEL = DEEPSEEK_MODEL_CHOICES[0][0]
DEEPSEEK_DEFAULT_CONTEXT_TOKENS = 128_000
DEEPSEEK_MAX_CONTEXT_TOKENS = 1_000_000


@dataclass(frozen=True)
class AgentSpec:
    """One independent OpenClaw gateway agent.

    Attributes:
        index: 1-based agent index (agent-1, agent-2, ...).
        name: Directory/service slug such as ``agent-1``.
        host_port: Host port published to container gateway port 18789.
        telegram_bot_token: BotFather token or placeholder string.
        gateway_token: OpenClaw gateway auth token (never commit real values).
        bot_numeric_id: Telegram bot id from getMe, or placeholder.
        bot_username: Telegram bot username without @, or empty.
        provider_api_key: Optional model provider key (placeholder allowed).
        provider_name: Provider id such as ``deepseek``, or empty.
        model_primary: OpenClaw model ref ``provider/model``, or empty.
        context_tokens: Optional runtime context cap (agents.defaults.contextTokens).
        persona: Optional one-line role text for IDENTITY.md.
        channels: Enabled channel ids (subset of ``telegram``, ``discord``).
        discord_bot_token: Discord bot token or placeholder (never commit real values).
        discord_guild_id: Primary Discord guild/server id or placeholder.
        image: Optional per-agent container image override (e.g. local ffmpeg build).
    """

    index: int
    name: str
    host_port: int
    telegram_bot_token: str
    gateway_token: str
    bot_numeric_id: str
    bot_username: str = ""
    provider_api_key: str = ""
    provider_name: str = ""
    model_primary: str = ""
    context_tokens: int | None = None
    persona: str = ""
    channels: tuple[str, ...] = ("telegram",)
    discord_bot_token: str = ""
    discord_guild_id: str = "YOUR_DISCORD_GUILD_ID"
    image: str = ""

    def __post_init__(self) -> None:
        """Normalize and validate channel flags."""
        allowed = {"telegram", "discord"}
        raw = tuple(str(c).strip().lower() for c in self.channels if str(c).strip())
        if not raw:
            raw = ("telegram",)
        unknown = [c for c in raw if c not in allowed]
        if unknown:
            raise ValidationError(
                f"Unknown channels for {self.name}: {unknown!r}.",
                code="AGENT_BAD_CHANNEL",
                hint="Use only: telegram, discord.",
            )
        # freeze normalized unique order
        object.__setattr__(self, "channels", tuple(dict.fromkeys(raw)))

    def uses_telegram(self) -> bool:
        """True when Telegram channel should be configured."""
        return "telegram" in self.channels

    def uses_discord(self) -> bool:
        """True when Discord channel should be configured."""
        return "discord" in self.channels

    def to_public_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict with secrets removed."""
        data = asdict(self)
        data["telegram_bot_token"] = "***REDACTED***"
        data["gateway_token"] = "***REDACTED***"
        data["discord_bot_token"] = "***REDACTED***" if data.get("discord_bot_token") else ""
        if data.get("provider_api_key"):
            data["provider_api_key"] = "***REDACTED***"
        return data


@dataclass(frozen=True)
class StackSpec:
    """Full multi-agent stack description used to render files.

    Attributes:
        agents: Ordered agent specs (length >= 2).
        owner_telegram_id: Human operator numeric Telegram user id.
        openclaw_image: Container image reference.
        base_port: Host port for agent-1 (defaults to 18789).
        audit_group_chat_id: Optional shared audit supergroup id.
        llm_provider: Shared provider id when setup chose one (e.g. deepseek).
    """

    agents: tuple[AgentSpec, ...]
    owner_telegram_id: str
    openclaw_image: str = "ghcr.io/openclaw/openclaw:latest"
    base_port: int = 18789
    audit_group_chat_id: str = "AUDIT_GROUP_CHAT_ID"
    llm_provider: str = ""

    def __post_init__(self) -> None:
        """Validate minimum size and unique ports/names."""
        if len(self.agents) < 2:
            raise ValidationError(
                "Stack requires at least 2 agents.",
                code="STACK_MIN_AGENTS",
                hint="Pass agent_count >= 2 to setup/generate.",
            )
        names = [a.name for a in self.agents]
        if len(set(names)) != len(names):
            raise ValidationError(
                "Agent names must be unique.",
                code="STACK_DUP_NAME",
                hint="Use distinct agent-N directory names.",
            )
        ports = [a.host_port for a in self.agents]
        if len(set(ports)) != len(ports):
            raise ValidationError(
                "Host ports must be unique.",
                code="STACK_DUP_PORT",
                hint="Increase base_port spacing or reduce agent count.",
            )

    def peer_ids_for(self, agent: AgentSpec) -> list[str]:
        """Return allowlist ids for owner plus every other agent bot id."""
        peers = [self.owner_telegram_id]
        for other in self.agents:
            if other.name != agent.name:
                peers.append(other.bot_numeric_id)
        return peers

    def uses_deepseek(self) -> bool:
        """True when any agent is configured for the DeepSeek provider."""
        if self.llm_provider == "deepseek":
            return True
        return any(a.provider_name == "deepseek" for a in self.agents)

    def to_public_dict(self) -> dict[str, Any]:
        """Return a redacted dict suitable for structured logs."""
        return {
            "agent_count": len(self.agents),
            "owner_telegram_id": self.owner_telegram_id,
            "openclaw_image": self.openclaw_image,
            "base_port": self.base_port,
            "audit_group_chat_id": self.audit_group_chat_id,
            "llm_provider": self.llm_provider,
            "agents": [a.to_public_dict() for a in self.agents],
        }


def parse_positive_int(raw: str, *, field_name: str, minimum: int = 1) -> int:
    """Parse a positive integer from user input.

    Args:
        raw: Raw string from CLI/env.
        field_name: Name used in error messages.
        minimum: Inclusive lower bound.

    Returns:
        Parsed integer.

    Raises:
        ValidationError: If parsing fails or value is below minimum.
    """
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{field_name} must be an integer, got {raw!r}.",
            code="INPUT_NOT_INT",
            hint=f"Provide a whole number for {field_name}.",
        ) from exc
    if value < minimum:
        raise ValidationError(
            f"{field_name} must be >= {minimum}, got {value}.",
            code="INPUT_TOO_SMALL",
            hint=f"Re-run and enter {field_name} >= {minimum}.",
        )
    return value


def parse_context_tokens(raw: str, *, field_name: str = "context_tokens") -> int:
    """Parse a context window cap within DeepSeek-safe bounds.

    Args:
        raw: Raw token count string.
        field_name: Name used in errors.

    Returns:
        Integer token cap between 1024 and DEEPSEEK_MAX_CONTEXT_TOKENS.
    """
    value = parse_positive_int(raw, field_name=field_name, minimum=1024)
    if value > DEEPSEEK_MAX_CONTEXT_TOKENS:
        raise ValidationError(
            f"{field_name} must be <= {DEEPSEEK_MAX_CONTEXT_TOKENS}, got {value}.",
            code="CONTEXT_TOO_LARGE",
            hint=(
                f"DeepSeek V4 native window is {DEEPSEEK_MAX_CONTEXT_TOKENS}. "
                f"Use a smaller runtime cap (default {DEEPSEEK_DEFAULT_CONTEXT_TOKENS})."
            ),
        )
    return value


def require_non_empty(raw: str, *, field_name: str) -> str:
    """Strip and require a non-empty string."""
    value = str(raw).strip()
    if not value:
        raise ValidationError(
            f"{field_name} must not be empty.",
            code="INPUT_EMPTY",
            hint=f"Provide a value for {field_name}.",
        )
    return value


def require_numeric_id(raw: str, *, field_name: str) -> str:
    """Require a numeric Telegram id string (digits only, optional leading -)."""
    value = require_non_empty(raw, field_name=field_name)
    body = value[1:] if value.startswith("-") else value
    if not body.isdigit():
        raise ValidationError(
            f"{field_name} must be numeric (optional leading -), got {value!r}.",
            code="INPUT_NOT_NUMERIC_ID",
            hint=(
                "Use a Telegram numeric user/bot/chat id. "
                "Bot ids come from getMe result.id. User ids come from @userinfobot "
                "or similar; do not use @usernames in allowFrom."
            ),
        )
    return value


def parse_yes_no(raw: str, *, default: bool) -> bool:
    """Parse a yes/no answer with a default when empty."""
    value = str(raw).strip().lower()
    if not value:
        return default
    if value in {"y", "yes", "true", "1"}:
        return True
    if value in {"n", "no", "false", "0"}:
        return False
    raise ValidationError(
        f"Expected yes/no, got {raw!r}.",
        code="INPUT_NOT_YES_NO",
        hint="Answer y or n (or press Enter for the default).",
    )


def mapping_get_str(data: Mapping[str, Any], key: str, default: str = "") -> str:
    """Read a string field from a mapping with a default."""
    value = data.get(key, default)
    return "" if value is None else str(value)
