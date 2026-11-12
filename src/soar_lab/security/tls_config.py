"""BL-SEC-003/004: central TLS-verification resolver.

Every ``<SERVICE>_VERIFY_TLS`` decision funnels through
:func:`verify_tls` — one place to audit which services run with
certificate verification off, one place to change the semantics.

Contract (ADR-0005): default ``True``; disabling requires an explicit
env value in ``{0,false,no,off}`` and is the caller's responsibility to
log — this module stays side-effect free so it can run at import time.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["verify_tls", "ca_verify", "FALSEY_ENV"]

# Values that explicitly disable verification — everything else (including
# a typo) keeps the safe default.
FALSEY_ENV = frozenset({"0", "false", "no", "off"})


def verify_tls(service: str, *, default: bool = True) -> bool:
    """Resolve TLS verification for *service*.

    Args:
        service: service name (``"misp"``, ``"shuffle-backend"`` — mapped
            to ``<NAME>_VERIFY_TLS``) or a full env-var name already ending
            in ``_VERIFY_TLS``.
        default: resolution when the var is unset (default True).

    Returns:
        ``False`` only when the env var carries an explicit falsey value.
    """
    var = (
        service
        if service.endswith("_VERIFY_TLS")
        else f"{service.upper().replace('-', '_')}_VERIFY_TLS"
    )
    return os.environ.get(var, str(default).lower()).strip().lower() not in FALSEY_ENV


def ca_verify(*, default: bool = True) -> bool | str:
    """``requests`` ``verify`` value pinned to the lab CA when reachable.

    Resolution order: the combined certifi+lab bundle mounted in soar_api
    (keeps public-CA endpoints working), then the bare lab CA mounted
    there, then the repo copy for host runs, then *default*.
    """
    for path in (
        Path("/app/certs/ca-bundle.crt"),
        Path("/app/certs/ca.crt"),
        Path(__file__).resolve().parents[3] / "infra" / "docker" / "config" / "certs" / "ca.crt",
    ):
        if path.exists():
            return str(path)
    return default
