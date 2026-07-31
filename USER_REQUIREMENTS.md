# USER_REQUIREMENTS - openclaw-telegram-agents

Maintained by Atlas (AI agent). Read and update on every behavior change.

## Goal

Run **N independent OpenClaw Gateway containers** (N >= 2) that communicate
only over Telegram bot-to-bot messaging. Default bootstrap is 2 agents
(`agent-1`, `agent-2`). First-time UX is `git clone` -> `make setup` -> `make up`.

## Hard constraints

1. Separate per agent: state, workspace, auth, Telegram token, gateway token,
   provider env, Docker network, host port.
2. Telegram is the only agent <-> agent path.
3. Forbidden paths: Redis, HTTP between containers, shared files between agents,
   shared Docker network, docker.sock, host network, and gateway multi-agent
   routing (`tools.agentToAgent.enabled=false`). Same-agent session tools are
   allowed inside each container (`tools.sessions.visibility: "agent"`) so an
   agent can recall its own other sessions (DM vs group). Do not deny
   `sessions_list` / `sessions_history`.
4. No real tokens in git. Placeholders only in committed files.
   Also never commit real Telegram user ids, bot ids, group chat ids, or bot usernames.
   Live `agents/*/state/openclaw.json`, `agents/*/workspace/**` (including IDENTITY.md), and `agents/stack-public.json` stay local/gitignored.
5. No automatic live Telegram send on compose build/start.
6. Do not invent OpenClaw keys (`botToBot`, Telegram `allowBots`).
7. No wildcard Telegram allowlists.
8. Never call `getUpdates` while OpenClaw long-polls that bot.
9. Never print bot tokens in scripts/logs/tests.
10. Python tooling via Docker; Makefile is the operator interface.
11. Flat tree; individual source files stay under ~300 lines.
12. Typed Python + docstrings on public functions; structured error codes/hints.
13. MIT license; public GitHub-ready docs (README, AGENTS.md, .env.example).

## Operator UX

Interactive `make setup` / `setup_agents.py` must ask:

1. How many agents? (min 2)
2. Authorized human Telegram **numeric** user id (with tip for @userinfobot)
3. Optional shared Telegram **group chat id** (supergroup `-100...`; required for group replies)
4. Whether to use DeepSeek as the model provider (default yes)
4. If DeepSeek: API key (hidden), same-settings-for-all?, default model choice,
   max context window tokens (default 128000, max 1000000)
5. Telegram bot token per agent
6. Optional short persona/role per agent (live `workspace/IDENTITY.md`, gitignored; public samples in `agents/templates/`)
7. Redacted summary + confirm before write

It should resolve bot ids via `getMe` when network allows, write compose + agent
dirs + live `.env` files (including `DEEPSEEK_API_KEY` when chosen), set
`agents.defaults.model.primary` + `contextTokens`, and print next steps
(BotFather bot-to-bot, `make up`, `make enable-deepseek`).

## Runtime shape (verified on OpenClaw 2026.6.34)

- Image: `ghcr.io/openclaw/openclaw:latest` (`OPENCLAW_IMAGE`)
- Cmd: `node dist/index.js gateway --bind lan --port 18789`
- Host ports: `18789 + (index-1)` -> container `18789`
- Service/dir names: `agent-1` .. `agent-N`
- Networks: `openclaw-agent-N-net` (one each)
- Healthcheck: `/healthz`
- Heartbeat: `every: "0m"` (disabled for all agents; keep disabled for new agents)
- Quiet Telegram/Discord: streaming mode `off` + verbose/reasoning/thinking off (final answers only)
- tools.sessions.visibility: `agent` (own sessions visible across DM/group)
- tools.agentToAgent.enabled: false
- tools.deny: conversations_send, conversations_turn
- Identity file: `workspace/IDENTITY.md` (not `agents.entries` on 2026.6.34)

## Allowlist policy

For each agent K: owner id + every other agent's bot numeric id.

Optional audit group key may remain placeholder until operator replaces it.

## Tests and quality gates

- `make test` -> pytest (models, compose isolation, config deny list, generator)
- `make lint` -> ruff check + format check
- `make doctor` -> config + lint + test
- Manual: `make test-a2a FROM=agent-1 TO_USER=...` (not part of unit tests)

## A2A success stages

1. Telegram transport ok:true
2. OpenClaw inbound acceptance
3. Model turn
4. Peer reply

## Acceptance criteria

- [x] MIT LICENSE, README, AGENTS.md, .gitignore, .env.example
- [x] Makefile: up down setup generate test lint health logs config doctor
- [x] Interactive setup for N>=2 with tokens + owner id + optional DeepSeek/model/context
- [x] Generated isolated compose (one network per agent)
- [x] Unit tests + ruff via Docker
- [x] Default 2-agent placeholder layout
- [ ] Live Telegram ok:true (manual; real tokens)
- [ ] Inbound processing on peer (manual)

## Out of scope

- Automatic multi-step delegation frameworks
- Shared orchestration buses
- Single-process multi-agent routing
