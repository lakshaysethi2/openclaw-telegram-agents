# AGENTS.md - maintainer guide for AI coding agents

You are maintaining **openclaw-telegram-agents**: N isolated OpenClaw Gateway
containers (minimum 2) that may talk to each other **only over Telegram**.

Human operators and smaller AI agents should be able to `git pull` and run
`make setup` without reading the whole history.

## Non-negotiable rules

1. **Telegram is the only agent <-> agent bus.**
2. **Never** add shared Docker networks, Redis, shared volumes, HTTP between
   agents, or Docker socket mounts.
3. **Never** enable OpenClaw internal A2A tools:
   `sessions_send`, `sessions_spawn`, `conversations_send`, `conversations_turn`
   (they stay in `tools.deny`).
4. **Never invent config keys** such as `botToBot: true` or Telegram `allowBots`.
   Peer bots are admitted via numeric `allowFrom` + BotFather bot-to-bot opt-in.
5. **Never commit secrets.** `agents/*/.env` is gitignored.
6. **Never print bot tokens** in logs, tests, or README examples.
7. **Never call `getUpdates`** while a gateway long-polls that bot.
8. **No wildcard allowlists** (`*`) for Telegram dm/group policy.
9. **Keep files under ~300 lines** and the tree flat (see layout below).
10. **Run Python via Docker** (`make test`, `make lint`, `make setup`).

## Read these first

| File | Why |
|------|-----|
| `USER_REQUIREMENTS.md` | Product requirements; update when behavior changes |
| `README.md` | Operator quick start |
| `lib_models.py` | Typed data structures (do not guess fields) |
| `lib_compose.py` / `lib_config.py` | Source of generated compose/config |
| `tests/` | Expected behavior; extend when changing generators |

## Layout (keep flat)

```text
.
├── AGENTS.md Makefile README.md LICENSE USER_REQUIREMENTS.md
├── setup_agents.py generate_stack.py scripts_health.py test_a2a.sh
├── lib_*.py                 # small libraries, typed + documented
├── tests/                   # pytest
├── docker-compose.yml       # GENERATED
└── agents/agent-N/          # per-agent state, workspace, auth, .env
```

Do **not** create deep package hierarchies unless necessary.

## Standard commands (always prefer Make)

```bash
make help          # list targets
make setup         # interactive: agent count, tokens, owner id
make generate      # placeholder 2-agent stack (no real tokens)
make up / make down
make ps / make logs SERVICE=agent-1
make health
make config
make test          # REQUIRED before claiming done
make lint          # REQUIRED before claiming done
make doctor        # config + lint + test
make test-a2a FROM=agent-1 TO_USER=other_bot_username
make enable-deepseek   # after make up, if DeepSeek was configured
```

Before every PR or handoff:

```bash
make doctor
```

## How generation works

1. `StackSpec` / `AgentSpec` in `lib_models.py` validate inputs.
2. `lib_compose.py` renders isolated services + networks.
3. `lib_config.py` renders `openclaw.json`, env examples, IDENTITY.md.
4. `lib_setup.py` holds interactive DeepSeek/model/context prompts.
5. `generate_stack.py` writes files non-interactively.
6. `setup_agents.py` prompts humans and can call Telegram `getMe`.
7. `enable_deepseek.py` installs `@openclaw/deepseek-provider` per agent.

If you change rendered output, update unit tests in `tests/` in the same change.

## OpenClaw compatibility notes (verified 2026.6.34)

- Image: `ghcr.io/openclaw/openclaw:latest`
- Cmd: `node dist/index.js gateway --bind lan --port 18789`
- Health: `GET /healthz` -> `{"ok":true,"status":"live"}`
- `agents.entries.*.identity` was **rejected** by config validation; identity
  lives in `workspace/IDENTITY.md`.
- Heartbeat off: `agents.defaults.heartbeat.every: "0m"`
- Gateway token via env `OPENCLAW_GATEWAY_TOKEN`
- Telegram token via env `TELEGRAM_BOT_TOKEN`
- DeepSeek: env `DEEPSEEK_API_KEY`, model refs `deepseek/deepseek-v4-flash` or
  `deepseek/deepseek-v4-pro`, runtime cap `agents.defaults.contextTokens`

## Allowlist rules

For agent K, `channels.telegram.allowFrom` must contain:

- owner human numeric Telegram user id
- numeric bot ids of **every other** agent (from `getMe` -> `result.id`)

Outbound peer targeting uses `@bot_username`, not numeric id.

## Success stages for A2A (never collapse these)

1. Telegram `sendMessage` `ok:true` (transport)
2. Target OpenClaw admits inbound update (logs)
3. Model turn runs (provider key required)
4. Target sends reply (e.g. `A2A_ACK`)

If stage 1 works and later stages fail: report blocker class; do not widen
allowlists.

## Logging and errors

Use `lib_logging.setup_logging` and `log_error(..., code=..., hint=...)`.
Error messages must include:

- what failed
- stable `error_code`
- explicit `hint` for the next command to run

## Editing safety checklist

- [ ] File still under ~300 lines (split if larger)
- [ ] Public functions have type hints + docstrings
- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] No secrets in git
- [ ] `USER_REQUIREMENTS.md` updated if behavior changed
- [ ] Compose still has **one network per agent**

## What not to build here

- Multi-agent orchestration inside one gateway process
- Shared message bus / Redis / MQTT between containers
- Automatic delegation workflows beyond manual transport test
- Host-network mode or privileged containers
