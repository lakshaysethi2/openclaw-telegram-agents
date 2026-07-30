# openclaw-telegram-agents

Isolated **multi-agent OpenClaw** gateways that communicate **only over Telegram**.

Each agent is a separate Docker container with its own state, workspace, auth,
bot token, gateway token, host port, and bridge network. There is no Docker DNS
path between agents.

Minimum agents: **2** (default layout: `agent-1`, `agent-2`).

License: [MIT](./LICENSE)

## Quick start (git pull -> running)

```bash
git clone <this-repo-url>
cd openclaw-telegram-agents   # or your local folder name

# 0) prerequisites: Docker + Compose v2
# 1) interactive setup (asks agent count, bot tokens, your Telegram user id)
make setup

# 2) start gateways
make up

# 3) health
make health
make ps
```

`make setup` will:

1. Ask how many agents (min 2)
2. Ask for your **numeric** Telegram user id (not `@username`)
3. Ask whether to use **DeepSeek** (API key, default model, context window)
4. Ask for one **BotFather token** per agent (hidden input)
5. Optionally set a short persona/role per agent
6. Call Telegram `getMe` to resolve each bot numeric id/username when possible
7. Show a redacted summary and write `docker-compose.yml`, `agents/agent-N/**`, `.env`

Then:

```bash
# BotFather: enable Bot-to-Bot Communication for every bot
make up
make enable-deepseek   # if DeepSeek was chosen during setup
make health
```

### Placeholder demo (no real tokens)

```bash
make generate   # writes agent-1 + agent-2 placeholders
make up
make health     # gateways live; Telegram channel will 404 until real tokens
```

## Make targets

| Target | Purpose |
|--------|---------|
| `make setup` | Interactive configure |
| `make generate` | Non-interactive 2-agent placeholders |
| `make up` / `make down` | Start/stop stack |
| `make ps` / `make logs` | Status / logs (`SERVICE=agent-1`) |
| `make health` | Probe `/healthz` on published ports |
| `make config` | `docker compose config` validation |
| `make test` | Pytest in Docker |
| `make lint` | Ruff in Docker |
| `make doctor` | config + lint + test |
| `make test-a2a FROM=agent-1 TO_USER=other_bot` | Manual Telegram transport test |
| `make enable-deepseek` | Install DeepSeek provider plugin in each agent |

## Architecture

```text
agent-1 (port 18789, net openclaw-agent-1-net)
    |  Telegram Bot API only
agent-2 (port 18790, net openclaw-agent-2-net)
    |  optional more agents: agent-3 @ 18791, ...
```

Hard isolation:

- one Docker network per agent
- no shared volumes between agents
- internal OpenClaw A2A tools denied
- no Redis / no docker.sock / no host network

## Configuration

| Path | Role |
|------|------|
| `.env` | Root image pin (`OPENCLAW_IMAGE`) |
| `agents/agent-N/.env` | `TELEGRAM_BOT_TOKEN`, `OPENCLAW_GATEWAY_TOKEN`, provider keys |
| `agents/agent-N/state/openclaw.json` | OpenClaw JSON5 config |
| `agents/agent-N/workspace/` | Agent workspace / identity |
| `agents/agent-N/auth/` | Auth-profile secrets dir |

### `.env` keys (per agent)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC...     # BotFather token for THIS agent
OPENCLAW_GATEWAY_TOKEN=long-random   # Gateway Control UI / API auth
DEEPSEEK_API_KEY=sk-...              # set by make setup when DeepSeek is chosen
# OPENAI_API_KEY=...                 # alternative providers
# ANTHROPIC_API_KEY=...
# OPENROUTER_API_KEY=...
```

When DeepSeek is enabled, `openclaw.json` also sets:

- `agents.defaults.model.primary` (e.g. `deepseek/deepseek-v4-flash`)
- `agents.defaults.contextTokens` (runtime context cap; default `128000`)

Root `.env.example` documents the image pin and points at per-agent token files.

### Allowlists

Numeric ids only. For each agent, `allowFrom` includes:

- your human Telegram user id
- every **other** agent's bot numeric id (`getMe` -> `result.id`)

## Manual A -> B transport test

```bash
make up
make test-a2a FROM=agent-1 TO_USER=agent_2_bot_username
make logs SERVICE=agent-2
```

### Success stages (keep separate)

1. Telegram transport (`ok: true`)
2. OpenClaw inbound acceptance (target logs)
3. Model turn (needs provider key)
4. Target reply (e.g. `A2A_ACK`)

Stage 1 alone is **not** full A2A success.

## Control UI

- agent-1: http://127.0.0.1:18789/
- agent-2: http://127.0.0.1:18790/

Paste that agent's `OPENCLAW_GATEWAY_TOKEN`.

## Developer / AI maintainer checks

```bash
make doctor
```

See [AGENTS.md](./AGENTS.md) for contribution rules optimized for smaller coding
agents (flat tree, typed Python, structured errors, file size limits).

## Requirements source

Product constraints live in [USER_REQUIREMENTS.md](./USER_REQUIREMENTS.md).
Update that file when behavior changes.

## Known limitations

1. Live A2A needs real bots, BotFather bot-to-bot opt-in, and real numeric ids.
2. OpenClaw Telegram has no `allowBots` config key on tested 2026.6.34.
3. Placeholder tokens yield Telegram 404 channel restarts; `/healthz` can still pass.
4. Do not run `getUpdates` against a bot while its gateway is polling.
5. Bind mounts may need `make chown-agents` (uid 1000).
6. Gateways bind `lan` on published ports - use strong gateway tokens and a host firewall.

## References

- OpenClaw Docker: https://docs.openclaw.ai/install/docker
- OpenClaw Telegram: https://docs.openclaw.ai/channels/telegram
- Bot loop protection: https://docs.openclaw.ai/channels/bot-loop-protection
- Image: `ghcr.io/openclaw/openclaw:latest`
