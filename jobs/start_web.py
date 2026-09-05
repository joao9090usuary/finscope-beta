"""Inicia o Streamlit atrás da borda HTTP endurecida do Revo."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def _terminate(processes: list[subprocess.Popen]) -> None:
    """Finaliza os dois processos sem deixar um serviço parcialmente ativo."""
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 8
    for process in processes:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def main() -> int:
    """Supervisiona Streamlit e Caddy; a falha de qualquer um encerra o contêiner."""
    public_port = os.getenv("PORT", "8501").strip()
    if not public_port.isdigit() or not 1 <= int(public_port) <= 65535:
        raise RuntimeError("PORT possui formato inválido.")

    environment = os.environ.copy()
    environment["PORT"] = public_port
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "streamlit_app.py",
                "--server.address=127.0.0.1",
                "--server.port=8502",
                "--server.headless=true",
            ],
            env=environment,
        ),
        subprocess.Popen(
            [
                "/usr/local/bin/caddy",
                "run",
                "--config",
                "/etc/caddy/Caddyfile",
                "--adapter",
                "caddyfile",
            ],
            env=environment,
        ),
    ]
    stopping = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        while not stopping:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return return_code if return_code else 1
            time.sleep(0.25)
        return 0
    finally:
        _terminate(processes)


if __name__ == "__main__":
    raise SystemExit(main())
