#!/usr/bin/env python3
"""H-04: JSON-schema conformance tests for the boundary data contracts.

Validates the three crossing formats — webhook alert payload, Cortex
observable submission and cortex_6 job document — plus the invariant that
every observable field declared in ``analyzer_matrix.OBSERVABLE_FIELDS``
maps to a property of the alert schema (the contract the guarded nodes
rely on when they read ``$exec.<field>``).

Dependency-free: ``_check`` implements the JSON-Schema subset these
schemas use (type / required / properties / enum / minLength / minimum /
maximum / additionalProperties ignored-by-design).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "setup" / "shuffle_workflow"))

from analyzer_matrix import OBSERVABLE_FIELDS  # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parent / "data"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _check(instance, schema: dict, path: str = "$") -> list[str]:
    """Return a list of violations (empty = conform)."""
    errs: list[str] = []
    stype = schema.get("type")
    if stype:
        types = stype if isinstance(stype, list) else [stype]
        pytypes = {
            "object": dict,
            "array": list,
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
        }
        ok = False
        for t in types:
            pt = pytypes.get(t)
            if pt is None:
                continue
            if t in ("integer", "number") and isinstance(instance, bool):
                continue  # bool is not a number here
            if isinstance(instance, pt):
                ok = True
                break
        if not ok:
            errs.append(f"{path}: expected {types}, got {type(instance).__name__}")
            return errs
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum {schema['enum']}")
    if isinstance(instance, str):
        ml = schema.get("minLength")
        if ml and len(instance) < ml:
            errs.append(f"{path}: shorter than minLength {ml}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required '{req}'")
        for key, subschema in (schema.get("properties") or {}).items():
            if key in instance:
                errs.extend(_check(instance[key], subschema, f"{path}.{key}"))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errs.extend(_check(item, schema["items"], f"{path}[{i}]"))
    return errs


class TestAlertSchema:
    def test_valid_alert_conforms(self):
        alert = {
            "alert_id": "A-1",
            "timestamp": "2026-11-10T15:00:00Z",
            "severity": 3,
            "hostname": "H1",
            "src_ip": "185.220.101.42",
            "domain": "evil-c2.example.com",
            "url": "http://evil-c2.example.com/x",
            "hash": "44d88612fea8a8f36de82e1278abb02f",
            "raw": "test",
        }
        assert _check(alert, _load("alert.schema.json")) == []

    def test_edge_alert_empty_observables_conforms(self):
        """Observables may be empty strings — the guard skips, not the schema."""
        alert = {"alert_id": "E-1", "timestamp": 1794319000, "severity": "low",
                 "src_ip": "", "domain": "", "url": "", "hash": ""}
        assert _check(alert, _load("alert.schema.json")) == []

    def test_missing_alert_id_rejected(self):
        errs = _check({"timestamp": 1, "severity": 2}, _load("alert.schema.json"))
        assert any("alert_id" in e for e in errs)

    def test_matrix_fields_covered_by_alert_schema(self):
        """Every OBSERVABLE_FIELDS token must map to an alert property."""
        props = _load("alert.schema.json")["properties"]
        token_to_prop = {
            "$exec.hash": "hash",
            "$exec.src_ip": "src_ip",
            "$exec.domain": "domain",
            "$exec.url": "url",
        }
        for field, spec in OBSERVABLE_FIELDS.items():
            prop = token_to_prop.get(spec["token"])
            assert prop is not None, f"{field}: token {spec['token']} unmapped"
            assert prop in props, f"{field}: alert schema lacks property '{prop}'"


class TestObservableSchema:
    def test_valid_observable(self):
        obs = {"data": "44d88612fea8a8f36de82e1278abb02f",
               "attributes": {"dataType": "hash", "tlp": 2}}
        assert _check(obs, _load("observable.schema.json")) == []

    def test_empty_data_rejected(self):
        obs = {"data": "", "attributes": {"dataType": "hash"}}
        assert _check(obs, _load("observable.schema.json"))

    def test_unknown_datatype_rejected(self):
        obs = {"data": "x", "attributes": {"dataType": "registry_key"}}
        assert _check(obs, _load("observable.schema.json"))


class TestCortexJobSchema:
    def test_success_job(self):
        job = {"status": "Success", "dataType": "ip", "workerName": "IP-API_1_1",
               "startDate": 1794319180000, "endDate": 1794319181000}
        assert _check(job, _load("cortex_job.schema.json")) == []

    def test_failure_job(self):
        job = {"status": "Failure", "dataType": "domain", "workerName": "RDAP",
               "errorMessage": "File parameter is missing"}
        assert _check(job, _load("cortex_job.schema.json")) == []

    def test_bad_status_rejected(self):
        job = {"status": "Exploded", "dataType": "ip", "workerName": "X"}
        assert _check(job, _load("cortex_job.schema.json"))
