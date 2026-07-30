"""Interactive prompt helpers for first-run multi-agent setup.

Kept separate from setup_agents.py so both stay under the ~300 line budget.
Never logs or prints full API keys / bot tokens.
"""

from __future__ import annotations

from collections.abc import Callable

from lib_models import (
    DEEPSEEK_DEFAULT_CONTEXT_TOKENS,
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_MAX_CONTEXT_TOKENS,
    DEEPSEEK_MODEL_CHOICES,
    ValidationError,
    parse_context_tokens,
    parse_yes_no,
    require_non_empty,
)

PromptFn = Callable[[str], str]
PasswordFn = Callable[[str], str]


def mask_secret(secret: str) -> str:
    """Return a short masked preview for operator confirmation."""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def prompt_yes_no(prompt: str, *, default: bool, input_fn: PromptFn) -> bool:
    """Ask a yes/no question with a default."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    return parse_yes_no(input_fn(prompt + suffix), default=default)


def prompt_deepseek_api_key(password_fn: PasswordFn) -> str:
    """Prompt for a DeepSeek API key without echoing it."""
    print("  Get a key at: https://platform.deepseek.com/api_keys")
    key = password_fn("  DeepSeek API key (input hidden): ").strip()
    key = require_non_empty(key, field_name="DEEPSEEK_API_KEY")
    print(f"  key accepted (masked): {mask_secret(key)}")
    return key


def prompt_model_choice(
    *,
    input_fn: PromptFn,
    label: str = "Default model",
) -> str:
    """Offer numbered DeepSeek models plus custom free-text ref."""
    print(f"  {label}:")
    for idx, (ref, desc) in enumerate(DEEPSEEK_MODEL_CHOICES, start=1):
        print(f"    {idx}) {ref}  - {desc}")
    print(f"    {len(DEEPSEEK_MODEL_CHOICES) + 1}) custom provider/model ref")
    raw = input_fn(
        f"  Choose 1-{len(DEEPSEEK_MODEL_CHOICES) + 1} [default 1 = {DEEPSEEK_DEFAULT_MODEL}]: "
    ).strip()
    if not raw:
        return DEEPSEEK_DEFAULT_MODEL
    if raw.isdigit():
        choice = int(raw)
        if 1 <= choice <= len(DEEPSEEK_MODEL_CHOICES):
            return DEEPSEEK_MODEL_CHOICES[choice - 1][0]
        if choice == len(DEEPSEEK_MODEL_CHOICES) + 1:
            custom = require_non_empty(
                input_fn("  Custom model ref (provider/model): "),
                field_name="model_primary",
            )
            if "/" not in custom:
                raise ValidationError(
                    f"Model ref must look like provider/model, got {custom!r}.",
                    code="MODEL_REF_INVALID",
                    hint="Example: deepseek/deepseek-v4-flash",
                )
            return custom
    # Allow pasting a full ref directly.
    if "/" in raw:
        return raw
    raise ValidationError(
        f"Invalid model choice: {raw!r}.",
        code="MODEL_CHOICE_INVALID",
        hint=f"Enter 1-{len(DEEPSEEK_MODEL_CHOICES) + 1} or a provider/model ref.",
    )


def prompt_context_tokens(*, input_fn: PromptFn, label: str) -> int:
    """Prompt for agents.defaults.contextTokens with a safe default."""
    print(
        f"  {label} max context window (tokens). "
        f"DeepSeek V4 native max is {DEEPSEEK_MAX_CONTEXT_TOKENS}; "
        f"runtime caps may be lower."
    )
    raw = input_fn(f"  Context tokens [{DEEPSEEK_DEFAULT_CONTEXT_TOKENS}]: ").strip()
    if not raw:
        return DEEPSEEK_DEFAULT_CONTEXT_TOKENS
    return parse_context_tokens(raw, field_name="context_tokens")


def prompt_llm_settings(
    *,
    agent_count: int,
    input_fn: PromptFn,
    password_fn: PasswordFn,
) -> tuple[str, str, list[str], list[int]]:
    """Prompt for optional DeepSeek provider + per-agent model/context.

    Returns:
        (provider_name, api_key, model_primary_per_agent, context_tokens_per_agent)
        provider_name is "" when the operator skips LLM setup.
    """
    print("\n--- Model provider ---")
    print("OpenClaw needs a model provider for agent replies (stage 3/4 of A2A).")
    use_deepseek = prompt_yes_no(
        "Use DeepSeek as the model provider?",
        default=True,
        input_fn=input_fn,
    )
    if not use_deepseek:
        print("  Skipping LLM setup. Add provider keys later in agents/*/.env")
        empty_models = [""] * agent_count
        empty_ctx = [0] * agent_count
        return "", "", empty_models, empty_ctx

    api_key = prompt_deepseek_api_key(password_fn)
    shared = prompt_yes_no(
        "Use the same default model and context window for every agent?",
        default=True,
        input_fn=input_fn,
    )

    models: list[str] = []
    contexts: list[int] = []
    if shared:
        model = prompt_model_choice(input_fn=input_fn, label="Shared default model")
        ctx = prompt_context_tokens(input_fn=input_fn, label="Shared")
        models = [model] * agent_count
        contexts = [ctx] * agent_count
    else:
        for i in range(1, agent_count + 1):
            print(f"\n  LLM settings for agent-{i}:")
            models.append(prompt_model_choice(input_fn=input_fn, label=f"agent-{i} default model"))
            contexts.append(prompt_context_tokens(input_fn=input_fn, label=f"agent-{i}"))

    return "deepseek", api_key, models, contexts


def prompt_persona(*, input_fn: PromptFn, agent_name: str) -> str:
    """Optional one-line persona for IDENTITY.md."""
    raw = input_fn(
        f"  Optional short role/persona for {agent_name} "
        "(Enter to skip, e.g. 'research assistant'): "
    ).strip()
    return raw[:200]


def print_setup_summary(
    *,
    agent_count: int,
    owner_id: str,
    provider: str,
    models: list[str],
    contexts: list[int],
    bot_labels: list[str],
) -> None:
    """Print a redacted summary before writing files."""
    print("\n=== Setup summary (secrets redacted) ===")
    print(f"  agents: {agent_count}")
    print(f"  owner_telegram_id: {owner_id}")
    print(f"  llm_provider: {provider or '(none - configure later)'}")
    for i, label in enumerate(bot_labels):
        model = models[i] if i < len(models) else ""
        ctx = contexts[i] if i < len(contexts) else 0
        extra = ""
        if provider:
            extra = f" model={model or '-'} context_tokens={ctx or '-'}"
        print(f"  - agent-{i + 1}: {label}{extra}")
    print("========================================\n")
