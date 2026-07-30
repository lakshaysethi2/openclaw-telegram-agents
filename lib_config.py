"""Generate per-agent OpenClaw config, env files, and workspace identity.

Uses only keys verified against OpenClaw 2026.6.34. Does not invent
Telegram ``allowBots`` / ``botToBot`` keys. Does not use ``agents.entries``
(rejected by that image's config validator).
"""

from __future__ import annotations

from textwrap import dedent

from lib_models import AgentSpec, StackSpec

DENIED_A2A_TOOLS: tuple[str, ...] = (
    "sessions_send",
    "sessions_spawn",
    "conversations_send",
    "conversations_turn",
)


def render_openclaw_json(stack: StackSpec, agent: AgentSpec) -> str:
    """Render JSON5 openclaw.json for one agent.

    Args:
        stack: Full stack (needed for peer allowlists).
        agent: Target agent.

    Returns:
        JSON5 document text.
    """
    allow_from = stack.peer_ids_for(agent)
    allow_lines = ",\n        ".join(f'"{item}"' for item in allow_from)
    deny_lines = ",\n      ".join(f'"{item}"' for item in DENIED_A2A_TOOLS)
    origins = [
        f"http://127.0.0.1:{agent.host_port}",
        f"http://localhost:{agent.host_port}",
    ]
    if agent.host_port != 18789:
        origins.extend(["http://127.0.0.1:18789", "http://localhost:18789"])
    origin_lines = ",\n        ".join(f'"{o}"' for o in origins)
    group_id = stack.audit_group_chat_id
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

          agents: {{
            defaults: {{
              workspace: "/home/node/.openclaw/workspace",
              heartbeat: {{ every: "0m" }},
              // model: {{ primary: "openai/gpt-5.5" }},
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
              groupPolicy: "allowlist",
              groups: {{
                "{group_id}": {{
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
    """Render ``.env`` or ``.env.example`` body for one agent.

    Args:
        agent: Agent specification.
        example: When True, force placeholder-style values for commits.

    Returns:
        dotenv file text.
    """
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
    provider = (
        "REPLACE_WITH_PROVIDER_API_KEY"
        if example or not agent.provider_api_key
        else agent.provider_api_key
    )
    return (
        dedent(
            f"""
        # Secrets for {agent.name}. Real .env is gitignored.
        # TELEGRAM_BOT_TOKEN is the BotFather token for this agent only.
        TELEGRAM_BOT_TOKEN={token}
        OPENCLAW_GATEWAY_TOKEN={gateway}
        # Model provider key (uncomment the provider you use):
        # OPENAI_API_KEY={provider}
        # ANTHROPIC_API_KEY={provider}
        # OPENROUTER_API_KEY={provider}
        """
        ).strip()
        + "\n"
    )


def render_identity_md(agent: AgentSpec, stack: StackSpec) -> str:
    """Render workspace IDENTITY.md for one agent."""
    peers = ", ".join(a.name for a in stack.agents if a.name != agent.name)
    return (
        dedent(
            f"""
        # {agent.name}

        Independent OpenClaw agent in a multi-agent Telegram mesh.

        - Peer agents ({peers}) are reached only over Telegram bot-to-bot messages.
        - Do not use internal OpenClaw session/delegation tools for peer agents.
        - Owner Telegram numeric id is allowlisted for human control.
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
        "# Per-agent Telegram bot tokens live in agents/<name>/.env",
        "# Example keys (filled by make setup / setup_agents.py):",
    ]
    for agent in stack.agents:
        lines.append(f"# agents/{agent.name}/.env -> TELEGRAM_BOT_TOKEN=...")
        lines.append(f"# agents/{agent.name}/.env -> OPENCLAW_GATEWAY_TOKEN=...")
    lines.append("")
    return "\n".join(lines)
