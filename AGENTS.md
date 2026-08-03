# AGENTS.md - maintainer guide for AI coding agents

You are maintaining **openclaw-telegram-agents**: N isolated OpenClaw Gateway
containers (minimum 2) that may talk to each other **only over Telegram**.

Human operators and smaller AI agents should be able to `git pull` and run
`make setup` without reading the whole history.

## Non-negotiable rules

1. **Telegram is the only agent <-> agent bus.**
2. **Never** add shared Docker networks, Redis, shared volumes, HTTP between
   agents, or Docker socket mounts.
3. **Telegram is the only cross-agent path.** Keep `tools.agentToAgent.enabled=false`
   and deny `conversations_send` / `conversations_turn`. Same-agent session tools
   (`sessions_list`, `sessions_history`, optional `sessions_send`/`sessions_spawn`)
   are allowed because each agent is an isolated container - set
   `tools.sessions.visibility: "agent"` so DM/group/cron sessions can recall each other.
4. **Never invent config keys** such as `botToBot: true` or Telegram `allowBots`.
   Peer bots are admitted via numeric `allowFrom` + BotFather bot-to-bot opt-in.
5. **Never commit secrets or operator identity.** Gitignore covers
   `agents/*/.env`, live `agents/*/state/openclaw.json`, and
   `agents/stack-public.json`. Do **not** commit real Telegram user ids,
   bot ids, group ids, bot usernames, tokens, or API keys. Use placeholders
   like `YOUR_TELEGRAM_USER_ID`, `PEER_BOT_NUMERIC_ID`, `AUDIT_GROUP_CHAT_ID`.
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
├── agents/templates/        # public-safe IDENTITY examples only
└── agents/agent-N/          # per-agent dirs; live secrets/workspace gitignored
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

## Agent-3 (Friend Bot) is hand-configured, NOT generated

`generate_stack.py` deliberately has **no** `--friend-bot` branch (removed
2026-08): a generated agent-3 config would lack the delivery plugins, the
exec allowlist, and the Discord channel config the live bot needs, so
regenerating it would produce an unguarded bot. Agent-3's live config lives in
gitignored `agents/agent-3/{state,workspace}` on the deploy host; do not
try to regenerate it.

### Agent-3 delivery enforcement layer (plugins in `state/extensions/`)

The live bot loads these delivery plugins (auto-discovered from
`state/extensions/*/openclaw.plugin.json`):

- `friendbot-safe` - neutralizes all @-mentions at delivery
- `friendbot-english` - English-only belt
- `friendbot-noask` - strips permission asks at delivery
- `friendbot-finalize` - run-level gate via the `before_agent_finalize` hook:
  quote deliveries must run `search.py` in the same turn and carry >=10
  `path:` citations; final replies must not narrate the process. Bounded:
  at most 3 revisions per run, each rule has its own `maxAttempts`.

Plugin sources are mirrored in `agents/agent-3/extensions/` (committed,
public-safe); deploy = copy to live `state/extensions/` + restart. Probe:
`node agents/agent-3/extensions/friendbot-finalize/test.mjs` (wired into
pytest as `tests/test_friendbot_finalize.py`).

## OpenClaw compatibility notes (verified 2026.6.34)

- Image: `ghcr.io/openclaw/openclaw:latest`
- Cmd: `node dist/index.js gateway --bind lan --port 18789`
- Health: `GET /healthz` -> `{"ok":true,"status":"live"}`
- `agents.entries.*.identity` was **rejected** by config validation; identity
  lives in `workspace/IDENTITY.md`.
- Heartbeat off: `agents.defaults.heartbeat.every: "0m"` (default for all new agents)
- Quiet chat defaults: `verboseDefault`/`reasoningDefault`/`thinkingDefault`/`blockStreamingDefault` = `off`
- Channel streaming final-only: `channels.telegram|discord.streaming.mode: "off"` (no thinking/tool drafts)
- Gateway token via env `OPENCLAW_GATEWAY_TOKEN`
- Telegram token via env `TELEGRAM_BOT_TOKEN`
- DeepSeek: env `DEEPSEEK_API_KEY`, model refs `deepseek/deepseek-v4-flash` or
  `deepseek/deepseek-v4-pro`, runtime cap `agents.defaults.contextTokens`
- Harness hooks (plugin SDK): `before_agent_finalize` accepts
  `{action:"revise", retryCandidates:[{instruction,maxAttempts}]}` to force one
  more model pass before a natural final reply ships (max 3 per run; skipped
  when the run had deterministic side effects). `message_sending` /
  `reply_payload_sending` mutate the outbound text.

## Allowlist rules

For agent K, `channels.telegram.allowFrom` must contain:

- owner human numeric Telegram user id
- numeric bot ids of **every other** agent (from `getMe` -> `result.id`)

Outbound peer targeting uses `@bot_username`, not numeric id.

## Maintaining this file

Update this file when the repo layout, generator behavior, or agent-3 deploy
path changes. Keep it a pointer-file: authoritative detail lives in
`README.md`, `USER_REQUIREMENTS.md`, and the live agent-3 state on the deploy
host.

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


## Public repo / secrets

Assume GitHub is public.

**Never commit:**
- `agents/*/.env`
- live `agents/*/state/openclaw.json`
- anything under `agents/*/workspace/` (especially personal `IDENTITY.md`)
- `agents/stack-public.json`

**Do commit:**
- `*.example` placeholders
- `agents/templates/*.IDENTITY.md.example`
- generators/tests/docs
- `docker-compose.yml` without secrets

Live identity stays in gitignored `workspace/IDENTITY.md`. Public persona samples
belong under `agents/templates/`.
