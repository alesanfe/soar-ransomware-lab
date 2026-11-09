"""STIX 2.1 bundle export use case (F6).

Converts the stored alert corpus into a STIX 2.1 bundle consumable by
any CTI tooling (MISP import, TAXII clients, threat-intel platforms):
one ``indicator`` per IoC found in the alert (SHA-256, IPv4, domain),
one ``grouping`` per alert referencing its indicators, plus the lab
``identity`` as producer.

IDs are deterministic (uuid5 on alert_id + ioc) so re-exporting the
same corpus yields a diff-stable bundle — same convention as
``scripts/quality/export_attack_stix.py``.

The bundle is exposed two ways: ``/api/v1/stix/bundle`` (raw export)
and the TAXII-lite read-only surface under ``/api/v1/taxii2/``
(discovery/collections/objects — see ``taxii_server.py`` and ADR-0011).
A full TAXII 2.x server (manifest, status, versioning, pagination)
remains out of lab scope by decision.
"""

import re
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

__all__ = ["StixExportUseCase"]

STIX_NS = uuid.UUID("00abedb4-aa42-466c-9c01-23307a531342")
STIX_SPEC_VERSION = "2.1"

_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$")

_IDENTITY_NAME = "SOAR Ransomware Lab"


def _sid(stix_type: str, key: str) -> str:
    return f"{stix_type}--{uuid.uuid5(STIX_NS, f'{stix_type}:{key}')}"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _iter_iocs(alert: dict[str, Any]) -> Iterable[tuple[str, str]]:
    """Yield ``(pattern_value, display_value)`` IoC pairs from an alert.

    Searches the alert root and its nested ``data`` payload for the
    IoC field names the simulator and ingested alerts use.
    """
    sources = [alert]
    data = alert.get("data")
    if isinstance(data, dict):
        sources.append(data)

    hash_fields = ("hash", "sha256", "file_hash", "md5")
    ip_fields = ("source_ip", "src_ip", "ip", "dest_ip", "c2_ip")
    domain_fields = ("domain", "c2_domain", "hostname_domain")

    for src in sources:
        for field in hash_fields:
            value = src.get(field)
            if isinstance(value, str) and _HASH_RE.match(value):
                yield f"[file:hashes.'SHA-256' = '{value.lower()}']", f"sha256:{value[:12]}"
        for field in ip_fields:
            value = src.get(field)
            if isinstance(value, str) and _IPV4_RE.match(value):
                yield f"[ipv4-addr:value = '{value}']", f"ipv4:{value}"
        for field in domain_fields:
            value = src.get(field)
            if isinstance(value, str) and _DOMAIN_RE.match(value):
                yield f"[domain-name:value = '{value.lower()}']", f"domain:{value}"


class StixExportUseCase:
    """Build a STIX 2.1 bundle from the stored alert corpus."""

    def __init__(self, alerts_provider: Callable[[], Iterable[dict[str, Any]]]) -> None:
        """Create the use case; ``alerts_provider`` returns alert dicts."""
        if alerts_provider is None:
            raise ValueError("alerts_provider is required for StixExportUseCase")
        self._alerts_provider = alerts_provider

    def build_bundle(self, limit: int = 1000) -> dict[str, Any]:
        """Export up to ``limit`` most recent alerts as a STIX bundle."""
        alerts = list(self._alerts_provider() or [])[: max(0, limit)]
        created = _now()
        objects: list[dict[str, Any]] = [self._identity(created)]
        seen_ids: set[str] = set()

        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            alert_id = str(alert.get("alert_id") or f"alert-{len(objects)}")
            indicator_refs: list[str] = []
            for pattern, label in _iter_iocs(alert):
                iid = _sid("indicator", f"{alert_id}:{pattern}")
                if iid in seen_ids:
                    indicator_refs.append(iid)
                    continue
                seen_ids.add(iid)
                indicator_refs.append(iid)
                objects.append(
                    {
                        "type": "indicator",
                        "spec_version": STIX_SPEC_VERSION,
                        "id": iid,
                        "created": created,
                        "modified": created,
                        "name": f"{label} ({alert_id})",
                        "description": f"IoC observed in lab alert {alert_id}",
                        "pattern": pattern,
                        "pattern_type": "stix",
                        "valid_from": created,
                        "created_by_ref": objects[0]["id"],
                    }
                )
            if not indicator_refs:
                continue
            objects.append(
                {
                    "type": "grouping",
                    "spec_version": STIX_SPEC_VERSION,
                    "id": _sid("grouping", alert_id),
                    "created": created,
                    "modified": created,
                    "name": f"Lab incident {alert_id}",
                    "context": "suspicious-activity",
                    "object_refs": indicator_refs,
                    "created_by_ref": objects[0]["id"],
                }
            )

        return {
            "type": "bundle",
            "id": _sid("bundle", f"ioc-export:{len(objects)}"),
            "objects": objects,
        }

    @staticmethod
    def _identity(created: str) -> dict[str, Any]:
        return {
            "type": "identity",
            "spec_version": STIX_SPEC_VERSION,
            "id": _sid("identity", _IDENTITY_NAME),
            "created": created,
            "modified": created,
            "name": _IDENTITY_NAME,
            "identity_class": "system",
        }
