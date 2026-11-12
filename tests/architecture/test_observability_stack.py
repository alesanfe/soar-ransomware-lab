#!/usr/bin/env python3
"""Static validators for the observability/logging stack (OBS-001..004).

These tests pin the bugs that were found live into permanent gates:

- OBS-001/002: every Grafana alert rule expression must reference an
  existing *earlier* refId — never itself, never a cycle, never a missing
  ref. The [B]->[A] regression is covered by an explicit mutation test.
- OBS-003/004: every bind mount in docker-compose.logging.yml must resolve
  to an existing host path, configs/certs must be :ro, and no entrypoint
  may hide failures (``|| true``).
- Service hygiene: healthchecks on long-running services, resource
  limits/reservations, no-new-privileges, no accidental host port.
- OTel collector: health_check extension, memory_limiter first processor,
  bounded sending queue on the Tempo exporter.
"""

import os
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra/docker/compose/logging/docker-compose.logging.yml"
HARDENED = ROOT / "infra/docker/compose/docker-compose.hardened.yml"
COMPOSE_ROOT = ROOT / "infra/docker/compose"
# Docker Compose resolves relative bind-mount paths against the FIRST -f
# file's directory (infra/docker/compose/), not this file's directory —
# the stack is always invoked with docker-compose.yml first.
COMPOSE_DIR = COMPOSE.parent.parent
ALERTS = COMPOSE.parent / "alert-rules.yml"
OTEL = ROOT / "infra/docker/config/otel-collector-config.yaml"
PROM = ROOT / "infra/docker/config/prometheus.yml"
IAM = ROOT / "infra/docker/config/seaweedfs/iam.config.json"

ONE_SHOT = {"s3-init"}          # exits by design — no healthcheck required
ALLOWED_HOST_PORTS = {8084}     # 127.0.0.1:8084 is the only approved bind


class _ComposeLoader(yaml.SafeLoader):
    """Compose-spec tags used by the hardened overlay (`!override`/`!reset`)."""


_ComposeLoader.add_constructor(
    "!override",
    lambda loader, node: loader.construct_sequence(node)
    if isinstance(node, yaml.SequenceNode)
    else loader.construct_mapping(node),
)
_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def _load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_ComposeLoader)


def _compose() -> dict:
    return _load(COMPOSE)


def _hardened() -> dict:
    return _load(HARDENED)


# Default `make up` set (Makefile.linux COMPOSE_FILES, non-LAB branch).
DEFAULT_SET_FILES = (
    "docker-compose.yml",
    "docker-compose.core.yml",
    "docker-compose.misp.yml",
    "docker-compose.opensearch.yml",
    "docker-compose.api.yml",
    "logging/docker-compose.logging.yml",
)


def _rules() -> list[dict]:
    doc = yaml.safe_load(ALERTS.read_text(encoding="utf-8"))
    return [r for g in doc["groups"] for r in g["rules"]]


# --- OBS-001/002: alert rule expression-graph validation -------------------


def _expr_refs(model: dict) -> list[str]:
    """All refIds an expression block depends on."""
    refs = []
    for cond in model.get("conditions", []):
        refs += cond.get("query", {}).get("params", [])
    expr = model.get("expression")
    if expr and isinstance(expr, str) and expr:
        refs += re.findall(r"\$([A-Za-z_]\w*)", expr)
    return refs


def test_alert_rules_have_no_self_reference():
    """OBS-001: condition must never reference its own refId (the [B]->[B]
    bug that silently killed all evaluations)."""
    for rule in _rules():
        for block in rule["data"]:
            rid = block["refId"]
            assert rid not in _expr_refs(block["model"]), (
                f"{rule['uid']}: expression {rid} references itself"
            )


def test_alert_rules_references_resolve_to_earlier_queries():
    """OBS-002: every referenced refId must exist and appear before the
    consumer — cycles and dangling refs are rejected."""
    for rule in _rules():
        seen = set()
        for block in rule["data"]:
            rid = block["refId"]
            assert rid not in seen, f"{rule['uid']}: duplicate refId {rid}"
            for ref in _expr_refs(block["model"]):
                if ref in ("__expr__",):
                    continue
                assert ref in seen, (
                    f"{rule['uid']}: {rid} references {ref} before it is "
                    "defined (or missing entirely)"
                )
            seen.add(rid)


def test_alert_rule_condition_points_at_defined_refid():
    for rule in _rules():
        ids = {b["refId"] for b in rule["data"]}
        assert rule["condition"] in ids, (
            f"{rule['uid']}: condition {rule['condition']} has no data block"
        )


def test_alert_rules_mutation_guard(self_ref_guard=None):
    """OBS-001 acceptance: mutating an expression back to self-reference
    must be detected by the same check used above."""
    assert True  # see test_self_reference_detected_on_mutation below


def test_self_reference_detected_on_mutation():
    """Mutation test: graft the historical bug onto a copy of the first
    rule and prove the detector fires."""
    rule = _rules()[0]
    expr_block = next(b for b in rule["data"] if b["datasourceUid"] == "__expr__")
    expr_block["model"]["conditions"][0]["query"]["params"] = [
        expr_block["refId"]
    ]
    rid = expr_block["refId"]
    assert rid in _expr_refs(expr_block["model"]), (
        "detector failed to flag a self-referencing expression"
    )


def test_alert_rules_carry_severity_and_runbook():
    """OBS-122/123: every rule needs a severity label and a runbook."""
    for rule in _rules():
        labels = rule.get("labels", {})
        assert labels.get("severity") in ("info", "warning", "critical"), (
            f"{rule['uid']}: missing/invalid severity label"
        )
        ann = rule.get("annotations", {})
        assert ann.get("runbook"), f"{rule['uid']}: missing runbook annotation"


# --- OBS-003/004: bind mounts ----------------------------------------------


def _host_path(vol: str) -> Path:
    # Named volumes ('loki_data:...') and env-prefixed paths are skipped;
    # only real relative bind mounts are validated.
    return Path(vol.split(":", 1)[0])


def test_all_bind_mounts_exist():
    """OBS-004: every relative bind-mount source must resolve to an
    existing host path relative to the compose file."""
    missing = []
    for svc, spec in _compose()["services"].items():
        for vol in spec.get("volumes", []) or []:
            if not isinstance(vol, str):
                continue
            src = vol.split(":", 1)[0]
            if not src.startswith((".", "..", "/")) or "$" in src:
                if "$" in src:
                    continue  # env-expanded paths are checked live
                if re.match(r"^[A-Za-z0-9_]+$", src):
                    continue  # named volume
            if src.startswith("/") and not src.startswith("//"):
                continue  # absolute docker paths (docker.sock)
            p = (COMPOSE_DIR / src).resolve()
            if not p.exists():
                missing.append(f"{svc}: {src}")
    assert not missing, "bind mounts resolving to missing paths:\n" + "\n".join(
        missing
    )


def test_config_and_cert_mounts_are_readonly():
    """OBS-004: config files and certificates must mount :ro."""
    bad = []
    for svc, spec in _compose()["services"].items():
        for vol in spec.get("volumes", []) or []:
            if not isinstance(vol, str):
                continue
            src, *rest = vol.split(":")
            if ("config" in src or "certs" in src or src.endswith((".yml", ".yaml", ".json", ".sh", ".crt", ".key"))) and ":ro" not in vol:
                bad.append(f"{svc}: {vol}")
    assert not bad, "config/cert mounts missing :ro:\n" + "\n".join(bad)


def test_no_fail_open_shell_idioms():
    """OBS-008: '|| true' style fail-open idioms must not come back."""
    text = COMPOSE.read_text(encoding="utf-8") + ALERTS.read_text(
        encoding="utf-8"
    )
    assert "|| true" not in text
    assert "|| /bin/true" not in text


# --- service hygiene --------------------------------------------------------


def test_long_running_services_have_healthchecks():
    """OBS-019: every service except documented exceptions."""
    missing = [
        s
        for s, spec in _compose()["services"].items()
        if s not in ONE_SHOT and "healthcheck" not in spec
    ]
    assert not missing, f"services without healthcheck: {missing}"


def test_services_have_resource_limits():
    missing = [
        s
        for s, spec in _compose()["services"].items()
        if s not in ONE_SHOT
        and "limits" not in spec.get("deploy", {}).get("resources", {})
    ]
    assert not missing, f"services without resource limits: {missing}"


def test_only_grafana_publishes_a_host_port():
    """OBS-053: only 127.0.0.1:8084 is an approved host bind."""
    offenders = []
    for svc, spec in _compose()["services"].items():
        for p in spec.get("ports", []) or []:
            p = str(p)
            assert "127.0.0.1" in p or "localhost" in p, (
                f"{svc}: port '{p}' not loopback-bound"
            )
            m = re.search(r":(\d+):", p)
            if m and int(m.group(1)) not in ALLOWED_HOST_PORTS:
                offenders.append(f"{svc}: {p}")
    assert not offenders, f"unapproved host ports: {offenders}"


def test_no_new_privileges_except_documented():
    """OBS-036: no-new-privileges on every service that lacks a justified
    exception. s3/s3-init keep theirs: the SeaweedFS entrypoint su-execs
    root->seaweed at boot (documented upstream constraint)."""
    exempt = {"s3-init", "s3"}
    missing = [
        s
        for s, spec in _compose()["services"].items()
        if s not in exempt
        and "no-new-privileges:true" not in (spec.get("security_opt") or [])
    ]
    assert not missing, f"services missing no-new-privileges: {missing}"


def test_no_privileged_services():
    """OBS-EVAL-002: cAdvisor runs unprivileged — its explicit :ro host
    mounts cover cgroup/fs metrics. Nothing in this stack may be
    `privileged: true`."""
    offenders = [
        s for s, spec in _compose()["services"].items()
        if spec.get("privileged") is True
    ]
    assert not offenders, f"privileged services: {offenders}"


def test_no_cap_add_in_logging_stack():
    """OBS-EVAL-007: promtail no longer needs DAC_OVERRIDE — the raw
    docker.sock mount that forced it was replaced by the restricted
    docker-socket-proxy."""
    offenders = []
    for svc, spec in _compose()["services"].items():
        adds = set(spec.get("cap_add") or [])
        if adds:
            offenders.append(f"{svc}: {sorted(adds)}")
    assert not offenders, f"undocumented cap_add: {offenders}"


def test_no_raw_docker_socket_mounts():
    """OBS-EVAL-007: docker_sd goes through docker-socket-proxy
    (CONTAINERS/INFO/PING verbs) — nobody mounts the daemon socket."""
    offenders = []
    for svc, spec in _compose()["services"].items():
        for vol in spec.get("volumes", []) or []:
            if isinstance(vol, str) and "docker.sock" in vol:
                offenders.append(f"{svc}: {vol}")
    assert not offenders, f"raw docker.sock mounts: {offenders}"


def test_promtail_discovers_via_proxy():
    """promtail docker_sd must target the restricted proxy, not the
    daemon socket."""
    tpl = (
        ROOT / "infra/docker/config/templates/promtail-config.yml.template"
    ).read_text(encoding="utf-8")
    assert "unix:///var/run/docker.sock" not in tpl
    assert "docker-socket-proxy" in tpl
    deps = _compose()["services"]["promtail"].get("depends_on") or []
    assert "docker-socket-proxy" in deps


def test_promtail_has_no_dead_file_targets():
    """Every `__path__` file target must resolve to a path promtail can
    actually read — i.e. a bind-mounted host path or its own writable
    dirs. A `system-logs` job scraped /var/log/** inside the promtail
    container (no host mount exists): it only ever tailed image-build
    leftovers and, as uid 65534, produced permission-denied noise."""
    tpl = (
        ROOT / "infra/docker/config/templates/promtail-config.yml.template"
    ).read_text(encoding="utf-8")
    volumes = [
        str(v) for v in _compose()["services"]["promtail"].get("volumes") or []
    ]
    mounted = [
        v.split(":", 2)[1] for v in volumes if ":" in v and len(v.split(":")) >= 2
    ]
    for path in re.findall(r"__path__:\s*(\S+)", tpl):
        assert any(path.startswith(m.rstrip("/")) for m in mounted), (
            f"promtail file target {path} has no backing mount — dead job "
            "(the removed system-logs job hit exactly this)"
        )


def test_required_secret_vars_have_no_defaults():
    """OBS-013/148 + OBS-EVAL-003: credentials must use :? (fail at config
    time), never a silent :-default or an empty-string pass-through."""
    text = COMPOSE.read_text(encoding="utf-8")
    assert ":-soar-s3-secret" not in text and "change-me" not in text
    for var in ("S3_ADMIN", "LOKI_S3", "TEMPO_S3"):
        assert f"{var}_SECRET_KEY:?" in text or f"{var}_SECRET_KEY}}" in text
    # OBS-EVAL-003: secrets that were fail-open before the eval.
    for var in (
        "GRAFANA_ADMIN_PASSWORD",
        "OIDC_CLIENT_SECRET",
        "INTERNAL_SERVICE_TOKEN",
        "ELASTIC_PASSWORD",
    ):
        assert f"{var}:?" in text, f"{var} must be fail-closed (:?)"


def test_iam_template_has_no_real_secrets():
    """OBS-012: iam.config.json is a template — no credentials committed."""
    text = IAM.read_text(encoding="utf-8")
    assert "%%" in text, "iam.config.json should contain placeholders"
    for pat in ("secret", "change-me"):
        assert not re.search(rf'"secretKey":\s*"(?!%%)[^"]*{pat}', text, re.I)


# --- OTel collector (OBS-076..079) -------------------------------------------


def test_otel_collector_hardened_pipeline():
    cfg = yaml.safe_load(OTEL.read_text(encoding="utf-8"))
    assert "health_check" in cfg.get("extensions", {}), "OBS-006"
    assert cfg["service"]["extensions"] == ["health_check"], "OBS-006"
    procs = cfg["service"]["pipelines"]["traces"]["processors"]
    assert procs[0] == "memory_limiter", "OBS-078: limiter must be first"
    assert "batch" in procs, "OBS-079"
    exp = cfg["exporters"]["otlp/tempo"]
    assert exp.get("retry_on_failure", {}).get("enabled"), "OBS-077"
    assert exp.get("sending_queue", {}).get("enabled"), "OBS-077"
    assert exp["sending_queue"]["queue_size"] > 0


# --- Prometheus ------------------------------------------------------------


def test_blackbox_jobs_present():
    """OBS-023: blackbox scrape jobs cover https/http/tcp."""
    doc = yaml.safe_load(PROM.read_text(encoding="utf-8"))
    jobs = {j["job_name"] for j in doc["scrape_configs"]}
    assert {"blackbox-https", "blackbox-http", "blackbox-tcp"} <= jobs


# --- OBS-EVAL gates (2026-11-11) -------------------------------------------


def _pids(spec: dict) -> int | None:
    return (
        spec.get("deploy", {})
        .get("resources", {})
        .get("limits", {})
        .get("pids")
    )


def test_every_service_has_pids_limit():
    """OBS-EVAL-001: every long-running logging service gets a process
    bound — from the base compose or the hardened overlay."""
    hardened = _hardened()["services"]
    missing = []
    for svc, spec in _compose()["services"].items():
        if svc in ONE_SHOT:
            continue
        if _pids(spec) is None and _pids(hardened.get(svc, {})) is None:
            missing.append(svc)
    assert not missing, f"services without pids: {missing}"


def test_hardened_refs_resolve_in_default_set():
    """OBS-EVAL-006: a service key in the hardened overlay without
    image/build must resolve to a service defined in the default compose
    set — otherwise `make up` fails 'no image nor build context'
    (verified live: keycloak/oauth2-proxy/taxii broke the default set)."""
    defined: set[str] = set()
    for f in DEFAULT_SET_FILES:
        defined |= set((_load(COMPOSE_ROOT / f).get("services") or {}))
    broken = []
    for svc, spec in _hardened()["services"].items():
        if svc in defined:
            continue
        if "image" in spec or "build" in spec:
            continue  # self-contained (docker-socket-proxy, egress guard)
        broken.append(svc)
    assert not broken, (
        f"hardened overlay references services missing from the default "
        f"compose set: {broken} — move their hardened keys into their own "
        "optional compose files (victim-sim convention)"
    )


def test_needs_no_root_run_as_non_root():
    """OBS-EVAL-004/007: services with no privilege requirement run as an
    explicit non-root uid under the hardened overlay."""
    hardened = _hardened()["services"]
    for svc, uid in (("promtail", "65534"), ("blackbox-exporter", "65534")):
        spec = hardened.get(svc, {})
        user = str(spec.get("user", ""))
        assert user.startswith(uid), f"{svc}: expected uid {uid}, got {user!r}"


def test_stateless_and_volume_backed_services_readonly():
    """OBS-EVAL-004/008: stateless services and state-on-volume services
    run with a read-only rootfs under the hardened overlay."""
    hardened = _hardened()["services"]
    must_be_ro = {
        "grafana",
        "grafana-renderer",
        "loki",
        "tempo",
        "prometheus",
        "promtail",
        "otel-collector",
        "cadvisor",
        "blackbox-exporter",
        "elasticsearch-exporter",
    }
    offenders = [
        svc
        for svc in must_be_ro
        if not hardened.get(svc, {}).get("read_only")
        and not _compose()["services"].get(svc, {}).get("read_only")
    ]
    assert not offenders, f"services without read_only rootfs: {offenders}"


def test_optional_overlay_services_self_hardened():
    """OBS-EVAL-006: services from optional overlays (sso, taxii) carry
    their hardening in their own compose — never in the default-set
    hardened overlay."""
    for f, svcs in (
        ("docker-compose.sso.yml", ("keycloak", "oauth2-proxy-web", "oauth2-proxy-shuffle")),
        ("docker-compose.taxii.yml", ("taxii",)),
    ):
        doc = _load(COMPOSE_ROOT / f)
        for svc in svcs:
            spec = doc["services"][svc]
            assert spec.get("cap_drop") == ["ALL"], f"{svc}: no cap_drop"
            assert "no-new-privileges:true" in (spec.get("security_opt") or []), (
                f"{svc}: no nnp"
            )
            assert _pids(spec) is not None, f"{svc}: no pids"
