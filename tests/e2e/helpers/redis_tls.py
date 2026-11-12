"""Shared Redis connection kwargs for E2E tests.

The lab Redis serves TLS-only on :6379 (lab PKI, ``--port 0
--tls-port 6379``). Tests running inside ``soar_api`` must speak
``rediss://`` against the mounted CA; the same code keeps working in
plain environments because the kwargs are only applied when the CA
file exists.
"""

import os
from pathlib import Path

CA_CANDIDATES = (
    "/app/certs/ca.crt",
    "infra/docker/config/certs/ca.crt",
)


def redis_ca() -> str | None:
    for cand in CA_CANDIDATES:
        if Path(cand).exists():
            return cand
    return os.environ.get("REDIS_CA_CERT") or None


def redis_kwargs(host: str = "redis", port: int = 6379, password: str | None = None,
                 **extra) -> dict:
    """kwargs for ``redis.Redis``/``redis.asyncio.Redis`` — TLS when the lab
    CA is present, plain otherwise."""
    kwargs: dict = {"host": host, "port": port, "password": password, **extra}
    ca = redis_ca()
    if ca:
        kwargs.update(
            ssl=True,
            ssl_ca_certs=ca,
            ssl_cert_reqs="required",
        )
    return kwargs
