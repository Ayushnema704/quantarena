#!/usr/bin/env python3
"""Wait for Redis and Postgres to accept connections after docker compose up."""
import socket
import sys
import time

HOSTS = [
    ("redis", 6379),
    ("localhost", 6379),
    ("localhost", 5432),
]


def probe(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    deadline = time.time() + 60
    while time.time() < deadline:
        if any(probe(h, p) for h, p in HOSTS):
            print("At least one service port is open.")
            return 0
        time.sleep(2)
    print("Timeout waiting for services (is Docker running?)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
