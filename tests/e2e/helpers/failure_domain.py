"""Failure-domain classification (E6-03 / E12-05).

Maps exceptions/messages to a primary failure domain so a JUnit line or log
entry shows WHERE a failure lives instead of a generic "connection error".
Never reclassifies a failure into a pass — it only enriches diagnostics.
"""

from __future__ import annotations

from enum import Enum


class FailureDomain(str, Enum):
    PRODUCT = "PRODUCT"
    TEST_CODE = "TEST_CODE"
    RUNNER = "RUNNER"
    DOCKER = "DOCKER"
    HOST_CAPACITY = "HOST_CAPACITY"
    NETWORK = "NETWORK"
    TLS = "TLS"
    AUTH = "AUTH"
    OBS_RECOVERY = "OBS_RECOVERY"
    SECURITY_CONTROL = "SECURITY_CONTROL"
    CLEANUP = "CLEANUP"
    UNKNOWN = "UNKNOWN"


_TLS_MARKERS = (
    "certificate verify failed", "ssl:", "tls", "hostname mismatch",
    "ca bundle", "bad certificate", "cert", "handshake",
)
_AUTH_MARKERS = ("401", "403", "unauthorized", "forbidden", "authentication failure", "api key invalid")
_DNS_MARKERS = ("name or service not known", "temporary failure in name resolution", "gaierror")
_TCP_MARKERS = ("connection refused", "connection reset", "timed out", "timeout", "max retries")
_DOCKER_MARKERS = ("docker:", "no such container", "cannot connect to the docker daemon", "netns")
_HOST_MARKERS = ("no space left", "disk", "i/o error", "resource temporarily unavailable")
_OBS_MARKERS = ("never came back", "never recovered", "not ready", "w replay", "repopulat")
_SEC_MARKERS = ("egress", "allowlist", "impostor", "guard", "rejected")


def classify(exc_or_msg) -> tuple[FailureDomain, str]:
    """Return (domain, short_detail) for an exception or message string."""
    msg = str(exc_or_msg).lower()

    if any(m in msg for m in _HOST_MARKERS):
        return FailureDomain.HOST_CAPACITY, "host resource pressure"
    if "locked" in msg or any(m in msg for m in _AUTH_MARKERS):
        return FailureDomain.AUTH, "credential/auth failure"
    if any(m in msg for m in _TLS_MARKERS) and "certificat" in msg or "ca bundle" in msg:
        return FailureDomain.TLS, "TLS trust/verification failure"
    if any(m in msg for m in _DNS_MARKERS):
        return FailureDomain.NETWORK, "DNS resolution"
    if any(m in msg for m in _DOCKER_MARKERS):
        return FailureDomain.DOCKER, "docker control plane"
    if any(m in msg for m in _SEC_MARKERS):
        return FailureDomain.SECURITY_CONTROL, "security control verdict"
    if any(m in msg for m in _OBS_MARKERS):
        return FailureDomain.OBS_RECOVERY, "observability recovery"
    if any(m in msg for m in _TCP_MARKERS):
        return FailureDomain.NETWORK, "TCP connectivity"
    if "assert" in msg:
        return FailureDomain.PRODUCT, "assertion on product behaviour"
    return FailureDomain.UNKNOWN, msg[:80]


def junit_tag(domain: FailureDomain) -> str:
    """Prefix for JUnit-visible messages, e.g. ``[AUTH] analyst locked``."""
    return f"[{domain.value}]"
