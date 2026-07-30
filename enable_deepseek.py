#!/usr/bin/env python3
"""Install/enable the official DeepSeek provider plugin in each agent container.

Must run on the host (needs the docker CLI). Prefer: make enable-deepseek
Idempotent: already-installed plugins count as success.
Does not print API keys.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from lib_logging import log_error, setup_logging
from lib_paths import repo_root

PLUGIN_ID = "deepseek"
PLUGIN_SPEC = "@openclaw/deepseek-provider"


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
            top_level = bool(line) and not line[0].isspace() and line.endswith(":")
            if top_level:
                break
            if line.startswith("  ") and not line.startswith("   ") and line.endswith(":"):
                name = line.strip().rstrip(":")
                if name.startswith("agent-"):
                    names.append(name)
    return names


def run_compose(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run docker compose with captured text output."""
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=str(repo_root()),
        check=False,
        capture_output=True,
        text=True,
    )


def running_services() -> set[str]:
    """Return currently running compose service names."""
    proc = run_compose(["ps", "--status", "running", "--services"])
    return {line.strip() for line in (proc.stdout or "").splitlines() if line.strip()}


def exec_cli(service: str, cli_args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``node dist/index.js ...`` inside a service."""
    return run_compose(["exec", "-T", service, "node", "dist/index.js", *cli_args])


def combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    """Join stdout/stderr for simple substring checks."""
    return f"{proc.stdout or ''}\n{proc.stderr or ''}"


def plugin_ready(service: str) -> bool:
    """True when DeepSeek plugin is installed and loaded/enabled."""
    inspect = exec_cli(service, ["plugins", "inspect", PLUGIN_ID])
    text = combined_output(inspect).lower()
    if inspect.returncode != 0:
        return False
    if "status: loaded" in text or "status: enabled" in text:
        return True
    # Some builds print a table row instead of inspect prose.
    listed = exec_cli(service, ["plugins", "list"])
    listed_text = combined_output(listed).lower()
    return PLUGIN_ID in listed_text and "enabled" in listed_text


def ensure_enabled(service: str) -> None:
    """Best-effort enable of the deepseek plugin id in config."""
    proc = exec_cli(service, ["plugins", "enable", PLUGIN_ID])
    out = combined_output(proc)
    if proc.returncode == 0:
        print(f"==> {service}: enabled plugin id '{PLUGIN_ID}'")
    else:
        # Already enabled / unknown enable semantics should not hard-fail.
        print(f"==> {service}: enable note (exit {proc.returncode}): {out.strip()[:200]}")


def install_plugin(service: str) -> bool:
    """Install plugin; treat already-exists as success; fall back to --force."""
    attempts = [
        ["plugins", "install", PLUGIN_SPEC],
        ["plugins", "install", "--force", PLUGIN_SPEC],
        ["plugins", "update", PLUGIN_ID],
    ]
    for idx, args in enumerate(attempts, start=1):
        print(f"==> {service}: try {idx}: node dist/index.js {' '.join(args)}")
        proc = exec_cli(service, args)
        out = combined_output(proc)
        lowered = out.lower()
        if proc.returncode == 0:
            print(f"==> {service}: install/update OK")
            return True
        if "already exists" in lowered or "already installed" in lowered:
            print(f"==> {service}: plugin already present (treating as OK)")
            return True
        # Show a short non-secret snippet for debugging.
        snippet = out.strip().splitlines()
        if snippet:
            print(f"==> {service}: {snippet[-1][:200]}")
    return False


def ensure_service(service: str) -> bool:
    """Make sure DeepSeek plugin is ready on one agent service."""
    if plugin_ready(service):
        print(f"==> {service}: DeepSeek plugin already loaded")
        ensure_enabled(service)
        return True

    print(f"==> {service}: DeepSeek plugin not ready; installing")
    if not install_plugin(service):
        return False
    ensure_enabled(service)
    if plugin_ready(service):
        print(f"==> {service}: DeepSeek plugin ready")
        return True
    # Install may have succeeded but inspect needs a gateway restart.
    print(f"==> {service}: installed; restart may be required before inspect shows loaded")
    return True


def main() -> int:
    """Install/enable DeepSeek plugin for every agent-* service."""
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

    running = running_services()
    failed = False
    for service in services:
        if service not in running:
            print(f"FAIL: {service} is not running. Run: make up", file=sys.stderr)
            failed = True
            continue
        if not ensure_service(service):
            print(f"FAIL: {service} DeepSeek plugin not ready", file=sys.stderr)
            failed = True

    if failed:
        log_error(
            logger,
            "One or more DeepSeek plugin installs failed.",
            code="DEEPSEEK_PLUGIN_FAIL",
            hint=(
                "make up && make enable-deepseek. "
                "Ensure DEEPSEEK_API_KEY is in agents/*/.env. "
                "openclaw.json still carries a DeepSeek models catalog as fallback."
            ),
        )
        return 1

    print("DeepSeek ready on:", ", ".join(services))
    print("If models were just installed: make restart && make health")
    print("Then: make test-a2a FROM=agent-1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
