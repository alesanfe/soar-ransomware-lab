"""Observable → Analyzer compatibility matrix (H-02).

Formal declaration of which Cortex analyzers may receive which workflow
observable fields. Used by:

  - ``cortex_setup.discover_and_select_analyzers`` — only wire analyzers
    whose declared input type has a real field on the alert payload (H-03).
  - ``validate_workflows.py`` — conformance check: no wired analyzer may
    receive an observable it does not declare compatible (H-01).
  - ``analyzer_inventory.py`` — reports wired/skipped/incompatible (A-04).

Each entry:

  ``field``        workflow execution field token the value comes from
                   (``$exec.hash``, ``$exec.src_ip``, ``$exec.domain``,
                   ``$exec.url``).
  ``data_type``    Cortex ``dataType`` submitted to the analyzer API.
  ``validator``    name of a predicate in ``VALIDATORS`` — the guarded node
                   calls it before dispatching; non-passing input skips.
  ``requires``     optional set of prerequisites — ``"file"`` means the
                   analyzer needs an uploaded file artifact, which the
                   webhook payload can never carry.
"""

from __future__ import annotations

import ipaddress
import re

_HASH_RE = re.compile(
    r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$|^[a-fA-F0-9]{128}$"
)
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9](-?[a-zA-Z0-9])*\.)+[a-zA-Z]{2,63}$")
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _is_hash(v: str) -> bool:
    return bool(_HASH_RE.match(v.strip()))


def _is_ip(v: str) -> bool:
    try:
        ipaddress.ip_address(v.strip())
        return True
    except ValueError:
        return False


def _is_domain(v: str) -> bool:
    v = v.strip()
    return bool(v) and not _is_ip(v) and bool(_DOMAIN_RE.match(v))


def _is_url(v: str) -> bool:
    return bool(_URL_RE.match(v.strip()))


def _nonempty(v: str) -> bool:
    return bool(v and v.strip())


VALIDATORS = {
    "hash": _is_hash,
    "ip": _is_ip,
    "domain": _is_domain,
    "url": _is_url,
    "nonempty": _nonempty,
}

# Observable fields the alert payload can carry. Every analyzer input must
# resolve to one of these — there is no file-upload path via the webhook.
OBSERVABLE_FIELDS: dict[str, dict[str, str]] = {
    "hash": {"token": "$exec.hash", "data_type": "hash", "validator": "hash"},
    "ip": {"token": "$exec.src_ip", "data_type": "ip", "validator": "ip"},
    "domain": {"token": "$exec.domain", "data_type": "domain", "validator": "domain"},
    "url": {"token": "$exec.url", "data_type": "url", "validator": "url"},
}

# Cortex dataType name → our observable key, when they differ.
DATATYPE_TO_FIELD: dict[str, str] = {
    "hash": "hash",
    "ip": "ip",
    "domain": "domain",
    "url": "url",
    "fqdn": "domain",
    "uri_path": "url",
    "filename": "hash",  # filename observables ride the hash field
    "mail": "domain",
    "mail_subject": "hash",
    "regexp": "hash",
    "other": "hash",
    "file": "file",  # never satisfiable via webhook
}

# Analyzer base name (version suffix stripped) → observable keys it may
# consume, best-known. An analyzer not listed falls back to its declared
# Cortex dataTypes intersected with OBSERVABLE_FIELDS.
ANALYZER_INPUTS: dict[str, list[str]] = {
    # hash
    "Hashdd_Status": ["hash"],
    "TeamCymruMHR": ["hash"],
    "Maltiverse_Report": ["hash", "ip", "domain", "url"],
    "Cyberprotect_ThreatScore": ["hash", "ip", "domain", "url"],
    "CyberCrime-Tracker": ["ip", "domain", "url"],
    "ScanMalware": ["ip", "domain", "url"],
    # ip
    "IP-API": ["ip"],
    "DShield_lookup": ["ip"],
    "Abuse_Finder": ["ip", "domain", "url"],
    "Mnemonic_pDNS_Public": ["ip"],
    "GoogleDNS_resolve": ["ip", "domain"],
    "RDAP": ["ip", "domain"],
    # domain
    "DomainMailSPFDMARC": ["domain"],
    # url
    "MSDefenderOffice365_SafeLinksDecoder": ["url"],
    "UnshortenLink": ["url"],
    "Lookyloo_Screenshot": ["url"],
    # file-only (never wired — no file observable in the payload)
    "FileInfo": ["file"],
    "Yara": ["file"],
    "ClamAV_FileInfo": ["file"],
    "PDFPreview": ["file"],
    "QrDecode": ["file"],
    "Msg_Parser": ["file"],
    "Virusshare": ["file"],
}

# Analyzers that must never be wired regardless of declared compatibility —
# missing API keys/local data/known-broken upstream (documented in
# cortex_setup._SKIP_DYNAMIC_NAMES). Kept as data here so the validator can
# flag a wired-but-forbidden analyzer as an error, not just a skip.
FORBIDDEN_BASES: set[str] = {
    "Virusshare",
    "MISPWarningLists",
    "Robtex_IP_Query",
    "Robtex_Reverse_PDNS_Query",
    "Robtex_Forward_PDNS_Query",
    "MaxMind_GeoIP",
    "CIRCLHashlookup",
    "AIL_OnionLookup",
    "SpamhausDBL",
    "ThreatMiner",
    "StopForumSpam",
}


def base_name(analyzer_name: str) -> str:
    """Strip a trailing ``_X_Y``/``_X_Y_Z`` version suffix from an analyzer id."""
    return re.sub(r"(_\d+){1,3}$", "", analyzer_name)


def allowed_fields(analyzer_name: str, declared_datatypes: list[str]) -> list[str]:
    """Observable field keys this analyzer may consume on this workflow.

    ``ANALYZER_INPUTS`` overrides the declared list; otherwise intersect the
    analyzer's Cortex dataTypes with ``OBSERVABLE_FIELDS`` via
    ``DATATYPE_TO_FIELD``. ``file``-only analyzers return ``[]``.
    """
    base = base_name(analyzer_name)
    if base in FORBIDDEN_BASES:
        return []
    if base in ANALYZER_INPUTS:
        return [f for f in ANALYZER_INPUTS[base] if f in OBSERVABLE_FIELDS]
    fields = []
    for dt in declared_datatypes:
        f = DATATYPE_TO_FIELD.get(dt)
        if f and f in OBSERVABLE_FIELDS and f not in fields:
            fields.append(f)
    return fields


def validate_value(field: str, value: str) -> bool:
    """True when ``value`` passes the validator of observable ``field``."""
    spec = OBSERVABLE_FIELDS.get(field)
    if spec is None:
        return False
    return VALIDATORS[spec["validator"]](value)
