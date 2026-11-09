"""Sigma detection evaluation — bounded sigma-lite subset (F5).

pySigma + its ES backend is a heavy dependency for the lab; this module
implements the detection-relevant subset of the Sigma spec honestly:

- ``detection.<name>`` maps: ``field: value`` or ``field: [v1, v2]``
  (list = OR), with ``|contains``/``|startswith``/``|endswith``/``|re``
  /``|all`` modifiers.
- ``condition``: a single selection name, ``X and Y``, ``X or Y``, or
  ``1 of <prefix>*`` — the patterns real detection rules use most.
- ``detection.keywords``: plain strings matched (OR) against the alert
  JSON — Sigma keyword-search equivalent.
- Non-detection fields (``logsource``, ``level``, ``status``,
  ``falsepositives``) are carried as metadata only.

Anything outside that subset fails loudly at load time rather than
silently mis-evaluating — a partial match is worse than a clear error.
"""

import json
import re
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml

__all__ = ["SigmaRule", "SigmaEvalUseCase", "SigmaUnsupportedError"]

_FIELD_RE = re.compile(r"^(?P<field>[\w.\[\]]+)(?P<mods>(\|\w+)*)$")


class SigmaUnsupportedError(ValueError):
    """Rule uses a Sigma feature outside the supported subset."""


class SigmaRule(dict):
    """One loaded Sigma rule (raw YAML mapping + helpers)."""

    @property
    def title(self) -> str:
        return str(self.get("title") or "untitled")

    @property
    def level(self) -> str:
        return str(self.get("level") or "informational")


def _get_field(alert: dict[str, Any], dotted: str) -> Any:
    """Resolve ``a.b.c`` against the alert (root then ``data``)."""
    for root in (alert, alert.get("data") if isinstance(alert.get("data"), dict) else {}):
        node: Any = root
        for part in dotted.split("."):
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(part)
        if node is not None:
            return node
    return None


def _match_value(actual: Any, expected: Any, mods: list[str]) -> bool:
    if isinstance(expected, list):
        # List = OR over candidates (|all flips it to AND) — modifiers
        # are preserved so `field|contains: [a, b]` means "contains any".
        if "all" in mods:
            return all(_match_value(actual, e, mods) for e in expected)
        return any(_match_value(actual, e, mods) for e in expected)
    if isinstance(actual, (list, tuple)):
        # Alert field is a list (e.g. mitre_techniques): match when ANY
        # element satisfies the scalar comparison.
        return any(_match_value(a, expected, mods) for a in actual)
    return _match_scalar(actual, expected, mods)


def _match_scalar(actual: Any, expected: Any, mods: list[str]) -> bool:
    if "re" in mods:
        return isinstance(actual, str) and re.search(str(expected), actual) is not None
    if "contains" in mods:
        return str(expected).lower() in str(actual).lower()
    if "startswith" in mods:
        return str(actual).lower().startswith(str(expected).lower())
    if "endswith" in mods:
        return str(actual).lower().endswith(str(expected).lower())
    if isinstance(actual, (int, float)) and not isinstance(expected, bool):
        with suppress((TypeError, ValueError)):
            return actual == float(expected)
    return str(actual) == str(expected)


class SigmaEvalUseCase:
    """Load Sigma rules and evaluate them against stored alerts."""

    def __init__(self, rules: Iterable[SigmaRule] | None = None) -> None:
        self._rules = list(rules or [])

    @staticmethod
    def load_rules(rules_dir: str | Path) -> list[SigmaRule]:
        """Load every ``*.yml``/``*.yaml`` under ``rules_dir``.

        Raises:
            SigmaUnsupportedError: when a rule needs an unsupported
                feature (correlations, aggregations, wildcards outside
                ``1 of <prefix>*``).
        """
        rules: list[SigmaRule] = []
        path = Path(rules_dir)
        if not path.is_dir():
            return rules
        for file in sorted(path.glob("*.y*ml")):
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "detection" not in data:
                continue
            rule = SigmaRule(data)
            rule["_source_file"] = file.name
            rules.append(rule)
        return rules

    @property
    def rules(self) -> list[SigmaRule]:
        return self._rules

    def evaluate(self, rule: SigmaRule, alert: dict[str, Any]) -> bool:
        """Return True when the alert satisfies the rule's condition."""
        detection = rule.get("detection") or {}
        condition = str(detection.get("condition") or "").strip()
        if not condition:
            raise SigmaUnsupportedError(f"{rule.title}: missing condition")

        selections = {
            name: spec
            for name, spec in detection.items()
            if name != "condition" and isinstance(spec, dict)
        }
        keywords = detection.get("keywords")

        return self._eval_condition(condition, selections, keywords, alert, rule)

    def scan(self, alerts: Iterable[dict[str, Any]], limit: int = 5000) -> dict[str, Any]:
        """Evaluate all loaded rules over the corpus.

        Returns per-rule ``{title, level, matches, match_rate}`` plus
        corpus totals — the lab's configurable-detection coverage.
        """
        corpus = [a for a in alerts if isinstance(a, dict)][: max(0, limit)]
        results: list[dict[str, Any]] = []
        for rule in self._rules:
            try:
                matches = sum(1 for a in corpus if self.evaluate(rule, a))
                error = None
            except SigmaUnsupportedError as e:
                matches, error = 0, str(e)
            results.append(
                {
                    "rule": rule.title,
                    "file": rule.get("_source_file"),
                    "level": rule.level,
                    "matches": matches,
                    "match_rate": round(100.0 * matches / len(corpus), 2) if corpus else 0.0,
                    "error": error,
                }
            )
        return {
            "rules_loaded": len(self._rules),
            "alerts_scanned": len(corpus),
            "results": results,
        }

    def _eval_condition(
        self,
        condition: str,
        selections: dict[str, dict],
        keywords: Any,
        alert: dict[str, Any],
        rule: SigmaRule,
    ) -> bool:
        if condition in selections:
            return self._eval_selection(selections[condition], alert)
        if condition == "keywords":
            return self._eval_keywords(keywords, alert)

        m = re.fullmatch(r"1 of ([\w*]+)", condition)
        if m:
            prefix = m.group(1).rstrip("*")
            hits = [
                self._eval_selection(spec, alert)
                for name, spec in selections.items()
                if name.startswith(prefix)
            ]
            if not hits:
                raise SigmaUnsupportedError(
                    f"{rule.title}: condition '{condition}' matches no selection"
                )
            return any(hits)

        for op in (" and ", " or "):
            if op in condition:
                parts = [p.strip() for p in condition.split(op)]
                results = [
                    self._eval_condition(part, selections, keywords, alert, rule) for part in parts
                ]
                return all(results) if op == " and " else any(results)

        raise SigmaUnsupportedError(f"{rule.title}: unsupported condition '{condition}'")

    def _eval_selection(self, spec: dict, alert: dict[str, Any]) -> bool:
        for raw_field, expected in spec.items():
            m = _FIELD_RE.match(str(raw_field))
            if not m:
                raise SigmaUnsupportedError(f"bad field expression: {raw_field}")
            field = m.group("field")
            mods = [x for x in m.group("mods").split("|") if x]
            actual = _get_field(alert, field)
            if actual is None:
                return False
            if not _match_value(actual, expected, mods):
                return False
        return True

    def _eval_keywords(self, keywords: Any, alert: dict[str, Any]) -> bool:
        if not keywords:
            return False
        blob = json.dumps(alert, default=str).lower()
        words = keywords if isinstance(keywords, list) else [keywords]
        return any(str(w).lower() in blob for w in words)
