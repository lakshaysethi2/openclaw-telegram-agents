"""Generate per-agent OpenClaw config, env files, and workspace identity.

Uses only keys verified against OpenClaw 2026.6.34+. Does not invent
Telegram ``allowBots`` / ``botToBot`` keys. Does not use ``agents.entries``
(rejected by that image's config validator).
"""

from __future__ import annotations

from textwrap import dedent

from lib_models import AgentSpec, StackSpec

# Tools that look like a second agent-bus. Keep denied so Telegram stays the
# only cross-*agent* path. Same-agent session tools stay available (each agent
# runs in its own container, so sessions_* only sees that agent's sessions).
DENIED_CROSS_AGENT_TOOLS: tuple[str, ...] = (
    "conversations_send",
    "conversations_turn",
)
# Back-compat alias used by tests/docs imports.
DENIED_A2A_TOOLS: tuple[str, ...] = DENIED_CROSS_AGENT_TOOLS


def _model_defaults_block(agent: AgentSpec) -> str:
    """Render optional model + contextTokens inside agents.defaults."""
    lines: list[str] = [
        'workspace: "/home/node/.openclaw/workspace",',
        'heartbeat: { every: "0m" },',
    ]
    if agent.model_primary:
        lines.append(f'model: {{ primary: "{agent.model_primary}" }},')
    else:
        lines.append('// model: { primary: "deepseek/deepseek-v4-flash" },')
    if agent.context_tokens and agent.context_tokens > 0:
        lines.append(f"contextTokens: {agent.context_tokens},")
    return "\n              ".join(lines)


def _deepseek_provider_block(agent: AgentSpec) -> str:
    """Optional models.providers.deepseek catalog for Docker without npm plugin.

    Official path still prefers ``@openclaw/deepseek-provider`` (make enable-deepseek).
    This explicit provider block keeps OpenAI-compatible DeepSeek usable even if
    the plugin is not installed yet.
    """
    if agent.provider_name != "deepseek":
        return ""
    # contextWindow is the model native window; agents.defaults.contextTokens caps runtime.
    return dedent(
        """
          models: {
            mode: "merge",
            providers: {
              deepseek: {
                // Auth: process env DEEPSEEK_API_KEY from agents/<name>/.env
                baseUrl: "https://api.deepseek.com",
                api: "openai-completions",
                models: [
                  {
                    id: "deepseek-v4-flash",
                    name: "DeepSeek V4 Flash",
                    input: ["text"],
                    contextWindow: 1000000,
                    maxTokens: 384000,
                  },
                  {
                    id: "deepseek-v4-pro",
                    name: "DeepSeek V4 Pro",
                    input: ["text"],
                    contextWindow: 1000000,
                    maxTokens: 384000,
                  },
                ],
              },
            },
          },
        """
    ).rstrip()


def render_openclaw_json(stack: StackSpec, agent: AgentSpec) -> str:
    """Render JSON5 openclaw.json for one agent."""
    allow_from = stack.peer_ids_for(agent)
    allow_lines = ",\n                ".join(f'"{item}"' for item in allow_from)
    deny_lines = ",\n              ".join(f'"{item}"' for item in DENIED_CROSS_AGENT_TOOLS)
    origins = [
        f"http://127.0.0.1:{agent.host_port}",
        f"http://localhost:{agent.host_port}",
    ]
    if agent.host_port != 18789:
        origins.extend(["http://127.0.0.1:18789", "http://localhost:18789"])
    origin_lines = ",\n                ".join(f'"{o}"' for o in origins)
    group_id = stack.audit_group_chat_id
    model_block = _model_defaults_block(agent)
    provider_block = _deepseek_provider_block(agent)
    provider_section = f"\n{provider_block}\n" if provider_block else "\n"
    return (
        dedent(
            f"""
        {{
          // {agent.name} - isolated OpenClaw gateway.
          // Tokens come from agents/{agent.name}/.env (never commit real tokens).
          // allowFrom uses numeric Telegram ids only (owner + peer bot ids).

          gateway: {{
            mode: "local",
            bind: "lan",
            auth: {{ mode: "token" }},
            controlUi: {{
              allowedOrigins: [
                {origin_lines}
              ],
            }},
          }},
          {provider_section}
          agents: {{
            defaults: {{
              {model_block}
            }},
          }},

          channels: {{
            defaults: {{
              botLoopProtection: {{
                enabled: true,
                maxEventsPerWindow: 20,
                windowSeconds: 60,
                cooldownSeconds: 60,
              }},
            }},
            telegram: {{
              enabled: true,
              dmPolicy: "allowlist",
              allowFrom: [
                {allow_lines}
              ],
              // groupPolicy=allowlist blocks ALL groups until a real chat id is listed.
              // Supergroup keys look like "-100xxxxxxxxxx" (not AUDIT_GROUP_CHAT_ID).
              groupPolicy: "allowlist",
              groups: {{
                "{group_id}": {{
                  // Plain group text is ignored while requireMention is true.
                  // Test with: @bot_username hello
                  requireMention: true,
                  allowFrom: [
                    {allow_lines}
                  ],
                }},
              }},
              historyLimit: 0,
            }},
          }},

          tools: {{
            // Each gateway is one agent in its own container. Allow that agent
            // to list/read/send across its OWN sessions (DM vs group, etc.).
            // Default OpenClaw visibility is "tree" (current + subagents only),
            // which hides sibling sessions and causes "I don't remember that".
            sessions: {{
              visibility: "agent",
            }},
            // Still block gateway multi-agent routing if ever misconfigured.
            agentToAgent: {{
              enabled: false,
            }},
            deny: [
              {deny_lines}
            ],
          }},
        }}
        """
        ).strip()
        + "\n"
    )


def render_agent_env(agent: AgentSpec, *, example: bool = False) -> str:
    """Render ``.env`` or ``.env.example`` body for one agent."""
    token = (
        f"REPLACE_WITH_{agent.name.upper().replace('-', '_')}_TELEGRAM_BOT_TOKEN"
        if example
        else agent.telegram_bot_token
    )
    gateway = (
        f"REPLACE_WITH_{agent.name.upper().replace('-', '_')}_GATEWAY_TOKEN"
        if example
        else agent.gateway_token
    )
    lines = [
        f"# Secrets for {agent.name}. Real .env is gitignored.",
        "# TELEGRAM_BOT_TOKEN is the BotFather token for this agent only.",
        f"TELEGRAM_BOT_TOKEN={token}",
        f"OPENCLAW_GATEWAY_TOKEN={gateway}",
    ]
    if agent.provider_name == "deepseek" or agent.model_primary.startswith("deepseek/"):
        if example:
            lines.append("DEEPSEEK_API_KEY=REPLACE_WITH_DEEPSEEK_API_KEY")
        elif agent.provider_api_key:
            lines.append(f"DEEPSEEK_API_KEY={agent.provider_api_key}")
        else:
            lines.append("# DEEPSEEK_API_KEY=REPLACE_WITH_DEEPSEEK_API_KEY")
    else:
        lines.append("# Model provider key (uncomment the provider you use):")
        lines.append("# DEEPSEEK_API_KEY=REPLACE_WITH_DEEPSEEK_API_KEY")
        lines.append("# OPENAI_API_KEY=REPLACE_WITH_PROVIDER_API_KEY")
        lines.append("# ANTHROPIC_API_KEY=REPLACE_WITH_PROVIDER_API_KEY")
        lines.append("# OPENROUTER_API_KEY=REPLACE_WITH_PROVIDER_API_KEY")
    return "\n".join(lines) + "\n"


def render_identity_md(agent: AgentSpec, stack: StackSpec) -> str:
    """Render workspace IDENTITY.md for one agent."""
    peers = ", ".join(a.name for a in stack.agents if a.name != agent.name)
    persona = agent.persona.strip() or "Independent OpenClaw agent in a multi-agent Telegram mesh."
    model_line = (
        f"- Default model: `{agent.model_primary}`"
        if agent.model_primary
        else "- Default model: not set yet (configure provider in .env / openclaw.json)."
    )
    ctx_line = (
        f"- Context token cap: {agent.context_tokens}"
        if agent.context_tokens
        else "- Context token cap: provider/model default."
    )
    return (
        dedent(
            f"""
        # {agent.name}

        {persona}

        - Peer agents ({peers}) are reached only over Telegram bot-to-bot messages.
        - This container holds only {agent.name}. Use sessions_list + sessions_history
          when the human asks about something from another of YOUR chats/sessions
          (for example a group vs a DM). Those tools see this agent's sessions only.
        - Do not invent a path to peer agent internals; peers are other bots on Telegram.
        - Owner Telegram numeric id is allowlisted for human control.
        {model_line}
        {ctx_line}
        """
        ).strip()
        + "\n"
    )


def render_root_env_example(stack: StackSpec) -> str:
    """Render root ``.env.example`` with image pin and token slots."""
    lines = [
        "# Root compose settings. Copy to .env (gitignored).",
        f"OPENCLAW_IMAGE={stack.openclaw_image}",
        "",
        "# Optional: default owner id documented for operators (not read by compose).",
        f"# OWNER_TELEGRAM_ID={stack.owner_telegram_id}",
        "",
        "# Per-agent secrets live in agents/<name>/.env",
        "# Example keys (filled by make setup / setup_agents.py):",
    ]
    for agent in stack.agents:
        lines.append(f"# agents/{agent.name}/.env -> TELEGRAM_BOT_TOKEN=...")
        lines.append(f"# agents/{agent.name}/.env -> OPENCLAW_GATEWAY_TOKEN=...")
        if stack.uses_deepseek():
            lines.append(f"# agents/{agent.name}/.env -> DEEPSEEK_API_KEY=...")
    lines.append("")
    return "\n".join(lines)
