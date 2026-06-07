"""Docker sandbox configuration for contestant containers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SECCOMP_PATH = os.environ.get(
    "SECCOMP_PATH",
    str(ROOT / "infra" / "seccomp_profile.json"),
)
USE_ISOLATED_NETWORK = os.environ.get("SANDBOX_ISOLATED_NETWORK", "1") == "1"
DOCKER_RUNTIME = os.environ.get("DOCKER_RUNTIME", "runc")

_security_opt = ["no-new-privileges:true"]
# Skip adding seccomp file path to security options here. The Docker daemon
# expects a host-accessible seccomp JSON or inline JSON; passing a path that
# exists only inside the submission_api container can cause the daemon to try
# to decode the file and fail (see local Windows Docker setups). For local
# development we keep the default seccomp profile and avoid passing a file
# path to the daemon.

SANDBOX_CONFIG: dict[str, Any] = {
    "runtime": DOCKER_RUNTIME,
    "mem_limit": "256m",
    "memswap_limit": "256m",
    "cpu_quota": 100_000,
    "cpu_period": 100_000,
    "cpuset_cpus": os.environ.get("SANDBOX_CPUSET", "0"),
    "pids_limit": 256,
    "cap_drop": ["ALL"],
    "security_opt": _security_opt,
    "read_only": True,
    "tmpfs": {"/tmp": "size=32m,mode=1777"},
    "network_mode": "contestant_net" if USE_ISOLATED_NETWORK else "bridge",
    "ulimits": [
        {"Name": "nofile", "Soft": 1024, "Hard": 1024},
        {"Name": "nproc", "Soft": 128, "Hard": 128},
    ],
}


def container_kwargs(
    image: str,
    name: str,
    *,
    network: str | None = None,
    publish_port: int | None = None,
) -> dict[str, Any]:
    """Build docker-py run() kwargs from SANDBOX_CONFIG."""
    net = network or SANDBOX_CONFIG["network_mode"]
    kw: dict[str, Any] = {
        "image": image,
        "name": name,
        "detach": True,
        "runtime": SANDBOX_CONFIG["runtime"],
        "mem_limit": SANDBOX_CONFIG["mem_limit"],
        "memswap_limit": SANDBOX_CONFIG["memswap_limit"],
        "cpu_quota": SANDBOX_CONFIG["cpu_quota"],
        "cpu_period": SANDBOX_CONFIG["cpu_period"],
        "cpuset_cpus": SANDBOX_CONFIG["cpuset_cpus"],
        "pids_limit": SANDBOX_CONFIG["pids_limit"],
        "cap_drop": SANDBOX_CONFIG["cap_drop"],
        "security_opt": SANDBOX_CONFIG["security_opt"],
        "read_only": SANDBOX_CONFIG["read_only"],
        "tmpfs": SANDBOX_CONFIG["tmpfs"],
        "ulimits": SANDBOX_CONFIG["ulimits"],
        "labels": {"iicpc.submission": name, "iicpc.runtime": SANDBOX_CONFIG["runtime"]},
    }
    if net == "contestant_net":
        kw["network"] = net
    else:
        kw["network_mode"] = net
        if publish_port:
            kw["ports"] = {"8765/tcp": publish_port}
    return kw


def verify_runtime(client) -> dict[str, str]:
    """Return runtime info for health/docs."""
    return {
        "configured_runtime": SANDBOX_CONFIG["runtime"],
        "isolated_network": str(USE_ISOLATED_NETWORK),
        "seccomp": SECCOMP_PATH if Path(SECCOMP_PATH).exists() else "default",
    }
