"""Check OpenClaw /healthz endpoints for services in docker-compose.yml.

Parses published host ports from the compose file text (simple regex) so this
stays dependency-free and easy for smaller AI agents to follow.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request

from lib_logging import log_error, setup_logging
from lib_paths import compose_path, repo_root

PORT_RE = re.compile(r'"(\d+):18789"')


def published_host_ports(compose_text: str) -> list[int]:
    """Extract host ports mapped to container 18789.

    Args:
        compose_text: Full docker-compose.yml content.

    Returns:
        Sorted unique host ports.
    """
    ports = {int(match.group(1)) for match in PORT_RE.finditer(compose_text)}
    return sorted(ports)


def check_healthz(port: int, timeout_sec: float = 3.0) -> tuple[bool, str]:
    """GET /healthz on localhost port.

    Args:
        port: Host TCP port.
        timeout_sec: Request timeout.

    Returns:
        (ok, detail_message).
    """
    url = f"http://127.0.0.1:{port}/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ok = resp.status == 200 and "live" in body
            return ok, f"{url} -> {body.strip()}"
    except urllib.error.URLError as exc:
        return False, f"{url} -> URLError: {exc.reason!r}"
    except Exception as exc:  # noqa: BLE001 - surface any probe failure explicitly
        return False, f"{url} -> {type(exc).__name__}: {exc}"


def main() -> int:
    """CLI entry: return 0 when every discovered port is healthy."""
    logger = setup_logging()
    path = compose_path(repo_root())
    if not path.is_file():
        log_error(
            logger,
            f"Missing compose file: {path}",
            code="HEALTH_NO_COMPOSE",
            hint="Run: make generate   or   make setup",
        )
        return 2

    ports = published_host_ports(path.read_text(encoding="utf-8"))
    if not ports:
        log_error(
            logger,
            'No host ports matching "NNNN:18789" found in compose file.',
            code="HEALTH_NO_PORTS",
            hint="Regenerate compose with make generate, then make up.",
        )
        return 2

    failed = False
    for port in ports:
        ok, detail = check_healthz(port)
        print(("OK  " if ok else "FAIL") + " " + detail)
        if not ok:
            failed = True

    if failed:
        log_error(
            logger,
            "One or more health checks failed.",
            code="HEALTH_FAILED",
            hint="Run: make ps && make logs   Ensure make up completed.",
            context={"ports": ports},
        )
        return 1

    print(f"All healthy: {ports}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
