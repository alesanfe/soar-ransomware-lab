"""Architecture gates — network perimeter: egress guard + watcher (eval 39).

Static invariants for the zero-trust egress sidecar and the network
watcher so the properties in ``docs/39-eval-network-perimeter.md``
cannot regress: the guard must install a DROP chain, detect a dead
netns, keep NET_ADMIN on the sidecar only, and the watcher API stays
read-only with zero-trust attach verification.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARDENED = ROOT / "infra" / "docker" / "compose" / "docker-compose.hardened.yml"
NW = ROOT / "src" / "soar_lab" / "infrastructure" / "network_watcher"
HANDLER = NW / "_handler.py"
WATCHER = NW / "network_watcher.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _guard_block() -> str:
    return _read(HARDENED).split("api-egress-guard:", 1)[1].split("network-watcher:", 1)[0]


# --- egress guard ------------------------------------------------------------

def test_guard_chain_terminates_in_drop():
    body = _guard_block()
    assert "iptables -A EGRESS_GUARD -j DROP" in body


def test_guard_allows_private_ranges_only():
    body = _guard_block()
    for prefix in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
                   "192.168.0.0/16", "169.254.0.0/16"):
        assert f"-d {prefix} -j ACCEPT" in body, prefix


def test_guard_hooks_output_once():
    body = _guard_block()
    assert "-C OUTPUT -j EGRESS_GUARD" in body and "-I OUTPUT 1 -j EGRESS_GUARD" in body


def test_guard_detects_dead_netns():
    # E5-03b: after an api recreate the sidecar sleeps on a dead netns —
    # the watch loop must exit (restart re-attaches) when the api's
    # listener disappears. `$$` keeps compose from eating the variable.
    body = _guard_block()
    assert "nc -z 127.0.0.1 8000" in body
    assert "$$fails" in body and "exit 0" in body


def test_guard_healthcheck_checks_api_coresidency():
    # Rules in OUR netns are not enough — the api must still live in it.
    body = _guard_block()
    hc = body.split("healthcheck:", 1)[1].split("interval", 1)[0]
    assert "EGRESS_GUARD" in hc and "nc -z 127.0.0.1 8000" in hc


def test_guard_is_minimal_sidecar():
    body = _guard_block()
    assert "NET_ADMIN" in body
    assert "no-new-privileges:true" in body
    assert "read_only: true" in body
    assert 'network_mode: "service:api"' in body
    # pids bound — iptables + sleep needs almost nothing
    assert re.search(r"pids:\s*\d+", body)


def test_api_image_has_no_net_admin():
    # The cap lives ONLY on the sidecar — the api service must not carry
    # NET_ADMIN itself (compose.api + hardened api block).
    for f in ("docker-compose.api.yml", "docker-compose.hardened.yml"):
        src = _read(ROOT / "infra" / "docker" / "compose" / f)
        api = src.split("\n  api:", 1)[1].split("\n  ", 1)[0] if "\n  api:" in src else ""
        api = src.split("  api:", 1)[1]
        api = api.split("\n  ", 1)[0] + "\n" + api.split("\n  ", 1)[1][:4000]
        assert "NET_ADMIN" not in api.split("api-egress-guard")[0], f


# --- watcher -------------------------------------------------------------------

def test_watcher_api_is_read_only():
    src = _read(HANDLER)
    for verb in ("do_POST", "do_PUT", "do_DELETE", "do_PATCH"):
        assert f"def {verb}" not in src, verb
    assert "def do_GET" in src


def test_watcher_survives_client_disconnect():
    src = _read(HANDLER)
    assert "BrokenPipeError" in src and "ConnectionResetError" in src


def test_watcher_verifies_before_mutating():
    src = _read(WATCHER)
    attach = src.split("def attach(", 1)[1]
    verify_pos = attach.find("_verify_trust(")
    connect_pos = attach.find("net.connect(")
    assert 0 < verify_pos < connect_pos, "zero-trust check must precede net.connect"


def test_watcher_hybrid_trust_in_hardened():
    body = _read(HARDENED).split("network-watcher:", 1)[1]
    assert "WATCHER_TRUST_MODE=hybrid" in body
    assert "WATCHER_MANAGED_IMAGES" in body


def test_watcher_uses_proxy_in_hardened():
    body = _read(HARDENED).split("network-watcher:", 1)[1]
    assert "DOCKER_HOST=tcp://docker-socket-proxy:2375" in body
    assert "!reset []" in body  # hardened resets the raw socket mount


# --- NET-EVAL-2 (eval 58): internal-only db net + flow inventory --------------

MISP_YML = ROOT / "infra" / "docker" / "compose" / "docker-compose.misp.yml"
LOGGING_YML = ROOT / "infra" / "docker" / "compose" / "logging" / "docker-compose.logging.yml"
FLOW_INV = ROOT / "infra" / "docker" / "compose" / "flow-inventory.yml"
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"


def test_misp_db_net_is_internal_and_db_only_on_it():
    # internal: true removes the NAT gateway — misp-db gets real zero-egress.
    # misp-modules keeps misp_internal (legitimate enrichment egress).
    src = _read(MISP_YML)
    netdef = src.split("misp_db_net:", 1)[1]
    assert "internal: true" in netdef
    db = src.split("  misp-db:", 1)[1].split("\n  misp-modules:", 1)[0]
    db_nets = db.split("networks:", 1)[1].split("healthcheck", 1)[0]
    assert "misp_db_net" in db_nets and "misp_internal" not in db_nets


def test_db_plane_reachable_for_app_and_probe():
    # misp app must reach the db; blackbox needs the 3306 probe — both
    # attach the internal plane (attachment allowed; egress is not).
    misp = _read(MISP_YML).split("  misp:", 1)[1]
    assert "misp_db_net" in misp.split("healthcheck", 1)[0]
    bb = _read(LOGGING_YML).split("blackbox-exporter:", 1)[1].split("healthcheck", 1)[0]
    assert "misp_db_net" in bb


def test_flow_inventory_exists_and_covers_published_ports():
    # CIS 12.2: every published port must be documented with a purpose.
    import yaml

    inv = yaml.safe_load(_read(FLOW_INV))
    documented = {p["port_env"] for p in inv["published"]}
    published_envs = set()
    for f in COMPOSE_DIR.rglob("*.yml"):
        for m in re.finditer(r'"127\.0\.0\.1:\$\{(\w+)[^}]*\}', _read(f)):
            published_envs.add(m.group(1))
    missing = published_envs - documented
    assert not missing, f"published ports undocumented in flow-inventory: {sorted(missing)}"


def test_flow_inventory_covers_critical_flows():
    # The core authorized paths must be documented (src→dst:port).
    import yaml

    inv = yaml.safe_load(_read(FLOW_INV))
    pairs = {(f["src"], f["dst"], f["port"]) for f in inv["flows"]}
    for required in [
        ("api", "redis", 6379), ("api", "shuffle-backend", 5443),
        ("api", "thehive", 9443), ("misp", "misp-db", 3306),
        ("promtail", "loki", 3100), ("orborus", "shuffle-backend", 5001),
    ]:
        assert required in pairs, required


def test_no_tls_interception_declared():
    # TLS inspection is deliberately absent — cert pinning + mTLS would
    # break under MITM. The inventory must record that decision so a
    # future "security appliance" isn't added silently.
    src = _read(FLOW_INV)
    assert 'tls_inspection:   "NO' in src or "tls_inspection" in src
