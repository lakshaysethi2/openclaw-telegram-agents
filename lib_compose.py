"""Generate isolated docker-compose.yml content for N OpenClaw agents.

Each agent gets its own bridge network, host port, state/workspace/auth mounts,
and env file. Agents cannot reach each other over Docker DNS.
"""

from __future__ import annotations

from textwrap import dedent

from lib_models import AgentSpec, StackSpec


def _service_block(agent: AgentSpec) -> str:
    """Render one compose service for ``agent``."""
    net = f"{agent.name.replace('-', '_')}_net"
    return dedent(
        f"""
        {agent.name}:
          image: ${{OPENCLAW_IMAGE:-ghcr.io/openclaw/openclaw:latest}}
          container_name: openclaw-{agent.name}
          env_file:
            - agents/{agent.name}/.env
          environment:
            HOME: /home/node
            OPENCLAW_HOME: /home/node
            OPENCLAW_STATE_DIR: /home/node/.openclaw
            OPENCLAW_CONFIG_PATH: /home/node/.openclaw/openclaw.json
            OPENCLAW_CONFIG_DIR: /home/node/.openclaw
            OPENCLAW_WORKSPACE_DIR: /home/node/.openclaw/workspace
            OPENCLAW_DISABLE_BONJOUR: "1"
            TZ: UTC
          volumes:
            - ./agents/{agent.name}/state:/home/node/.openclaw
            - ./agents/{agent.name}/workspace:/home/node/.openclaw/workspace
            - ./agents/{agent.name}/auth:/home/node/.config/openclaw
          ports:
            - "{agent.host_port}:18789"
          networks:
            - {net}
          init: true
          restart: unless-stopped
          cap_drop:
            - NET_RAW
            - NET_ADMIN
          security_opt:
            - no-new-privileges:true
          command:
            - node
            - dist/index.js
            - gateway
            - --bind
            - lan
            - --port
            - "18789"
          healthcheck:
            test:
              [
                "CMD",
                "node",
                "-e",
                "fetch('http://127.0.0.1:18789/healthz').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))",
              ]
            interval: 30s
            timeout: 5s
            retries: 5
            start_period: 20s
        """
    ).rstrip()


def _network_block(agent: AgentSpec) -> str:
    """Render one dedicated bridge network for ``agent``."""
    net = f"{agent.name.replace('-', '_')}_net"
    return dedent(
        f"""
        {net}:
          name: openclaw-{agent.name}-net
          driver: bridge
        """
    ).rstrip()


def _indent_block(block: str, spaces: int = 2) -> str:
    """Indent every line of a YAML block (including blank lines' neighbors)."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in block.splitlines())


def render_compose(stack: StackSpec) -> str:
    """Render a full docker-compose.yml document for ``stack``.

    Args:
        stack: Validated multi-agent stack specification.

    Returns:
        YAML text for docker-compose.yml (Compose specification v2+).
    """
    header = dedent(
        """
        # GENERATED FILE. Prefer: python generate_stack.py  OR  make setup
        # Each agent is isolated: own state, workspace, auth, env, port, network.
        # Telegram is the only agent <-> agent path. Do not add shared networks.
        """
    ).strip()
    # _service_block/_network_block are dedented to column 0; re-indent under keys.
    services = "\n".join(_indent_block(_service_block(a)) for a in stack.agents)
    networks = "\n".join(_indent_block(_network_block(a)) for a in stack.agents)
    return f"{header}\n\nservices:\n{services}\n\nnetworks:\n{networks}\n"
