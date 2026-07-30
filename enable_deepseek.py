#!/usr/bin/env python3
"""Install the official DeepSeek provider plugin into each agent container.

Must run on the host (needs the docker CLI). Prefer: make enable-deepseek
Safe to re-run. Does not print API keys.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from lib_logging import log_error, setup_logging
from lib_paths import repo_root


def agent_service_names(compose_text: str) -> list[str]:
    """Parse top-level service names that look like agent-N."""
    names: list[str] = []
    in_services = False
    for raw in compose_text.splitlines():
        line = raw.rstrip()
        if line.startswith("services:"):
            in_services = True
            continue
        if in_services:
            top_level = line and not line[0].isspace() and line.endswith(":")
            if top_level:
                # next top-level key (e.g. networks:)
                break
            if line.startswith("  ") and not line.startswith("   ") and line.endswith(":"):
                name = line.strip().rstrip(":")
                if name.startswith("agent-"):
                    names.append(name)
    return names


def install_for_service(service: str) -> int:
    """Run openclaw plugins install inside one compose service."""
    attempts = [
        [
            "docker",
            "compose",
            "exec",
            "-T",
            service,
            "node",
            "dist/index.js",
            "plugins",
            "install",
            "@openclaw/deepseek-provider",
        ],
        [
            "docker",
            "compose",
            "exec",
            "-T",
            service,
            "openclaw",
            "plugins",
            "install",
            "@openclaw/deepseek-provider",
        ],
        [
            "docker",
            "compose",
            "exec",
            "-T",
            service,
            "npx",
            "--yes",
            "openclaw",
            "plugins",
            "install",
            "@openclaw/deepseek-provider",
        ],
    ]
    for idx, cmd in enumerate(attempts, start=1):
        label = " ".join(cmd[5:])
        print(f"==> {service}: try {idx}: {label}")
        proc = subprocess.run(cmd, cwd=str(repo_root()), check=False)
        if proc.returncode == 0:
            print(f"==> {service}: OK")
            return 0
    return 1


def main() -> int:
    """Install DeepSeek plugin for every agent-* service."""
    logger = setup_logging()
    if shutil.which("docker") is None:
        log_error(
            logger,
            "docker CLI not found on PATH.",
            code="NO_DOCKER",
            hint="Run on the host: make enable-deepseek  (not inside a container)",
        )
        return 2

    compose = Path(repo_root()) / "docker-compose.yml"
    if not compose.is_file():
        log_error(
            logger,
            f"Missing {compose}",
            code="NO_COMPOSE",
            hint="Run: make setup   or   make generate",
        )
        return 2

    services = agent_service_names(compose.read_text(encoding="utf-8"))
    if not services:
        log_error(
            logger,
            "No agent-* services found in docker-compose.yml",
            code="NO_AGENT_SERVICES",
            hint="Regenerate the stack with make setup.",
        )
        return 2

    failed = False
    for service in services:
        # Ensure service is running before exec.
        ps = subprocess.run(
            ["docker", "compose", "ps", "--status", "running", "--services"],
            cwd=str(repo_root()),
            check=False,
            capture_output=True,
            text=True,
        )
        running = {line.strip() for line in (ps.stdout or "").splitlines() if line.strip()}
        if service not in running:
            print(f"FAIL: {service} is not running. Run: make up", file=sys.stderr)
            failed = True
            continue
        code = install_for_service(service)
        if code != 0:
            failed = True
            print(f"FAIL: {service} plugin install failed", file=sys.stderr)

    if failed:
        log_error(
            logger,
            "One or more DeepSeek plugin installs failed.",
            code="DEEPSEEK_PLUGIN_FAIL",
            hint=(
                "make up && make enable-deepseek. "
                "Ensure DEEPSEEK_API_KEY is in agents/*/.env. "
                "If the plugin CLI is unavailable, model catalog is still in openclaw.json."
            ),
        )
        return 1

    print("DeepSeek plugin install attempted for:", ", ".join(services))
    print("Restart gateways: make restart && make health")
    return 0


if __name__ == "__main__":
    sys.exit(main())
