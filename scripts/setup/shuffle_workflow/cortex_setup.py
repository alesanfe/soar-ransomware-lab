"""Cortex analyzer discovery and installation.

Discovers installed Cortex analyzers, installs any missing ones from
the catalog, selects the primary hash/IP analyzers, and dynamically
wires any additional installed analyzers into the workflow.

Uses :class:`soar_lab.infrastructure.integrations.cortex.client.CortexClient`
for all HTTP interactions with the Cortex API.
"""

# NOTE: All ``requests`` calls in this module use ``verify=False`` because
# the lab uses self-signed certificates in the internal Docker network.
# This is safe in the lab context but must NOT be used in production.

from __future__ import annotations

import base64
import logging
import re
from typing import Any

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

from . import config
from .utils import action, branch, param, pos
from .workflow_actions import (
    ACT_CALC_DECISION,
    ACT_THEHIVE,
)

logger = logging.getLogger(__name__)

# Optional: use the dedicated CortexClient if the package is installed
try:
    from soar_lab.infrastructure.integrations.cortex.client import CortexClient

    _CORTEX_CLIENT_AVAILABLE = True
except ImportError:
    CortexClient = None  # type: ignore[assignment, misc]
    _CORTEX_CLIENT_AVAILABLE = False


_WANTED_ANALYZERS = [
    "DShield_lookup_1_0",
    "Mnemonic_pDNS_Public_3_0",
    "GoogleDNS_resolve_1_0_0",
    "IP-API_1_1",
    "ValidateObservable_1_0",
    "Hashdd_Status_2_0",
    "DomainMailSPFDMARC_1_2",
]

# Analyzers that fail due to missing API keys, local data, or bugs.
# Excluded from both _WANTED_ANALYZERS and dynamic wiring.
_SKIP_DYNAMIC_NAMES = {
    "DNSdumpster_report",
    "DNS_Lookingglass",
    "UnshortenLink",
    "Lookyloo_Screenshot",
    # Missing API keys / config
    "GoogleSafebrowsing",
    "ZscalerZIA_URLLookup",
    "Virusshare_2_0",
    "NSRL",
    "MISPWarningLists",
    # Analyzer bugs / wrong input
    "Crt_sh_Transparency_Logs_1_0",
    "Robtex_IP_Query_1_0",
    "Robtex_Reverse_PDNS_Query_1_0",
    "Robtex_Forward_PDNS_Query_1_0",
    "MaxMind_GeoIP_4_0",
    "CIRCLHashlookup",
    "AIL_OnionLookup",
    "SpamhausDBL",
    "ThreatMiner",
    "StopForumSpam",
}


def _build_cortex_client(cortex_basic: str) -> Any:
    """Build a CortexClient from the Basic auth header.

    Falls back to ``None`` if the client class is not available (e.g.
    when running outside the installed package).
    """
    if not _CORTEX_CLIENT_AVAILABLE:
        return None
    # Decode the Basic auth header to extract user/password
    try:
        decoded = base64.b64decode(cortex_basic).decode()
        user, password = decoded.split(":", 1)
    except Exception:
        user, password = "admin", ""
    return CortexClient(
        base_url=config.CORTEX_URL,
        api_key="",
        admin_user=user,
        admin_password=password,
        verify_ssl=False,
        timeout=60,
    )


def _cortex_install_analyzer(definition_id: str, cortex_basic: str) -> bool:
    """Try to enable a Cortex analyzer for the org from its catalog definition.

    Uses ``CortexClient.install_analyzer`` when available; falls back to
    a raw HTTP POST otherwise.
    """
    client = _build_cortex_client(cortex_basic)
    if client is not None:
        try:
            client.install_analyzer(definition_id)
            return True
        except Exception as _install_e:
            # Check if it's a 409 Conflict (already installed)
            if "409" in str(_install_e):
                return True
            logger.warning("[cortex] Could not install %s: %s", definition_id, _install_e)
            return False
    # Fallback: raw requests
    import requests

    try:
        resp = requests.post(
            f"{config.CORTEX_URL}/api/organization/analyzer/{definition_id}",
            headers={
                HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {cortex_basic}",
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            },
            json={
                "name": definition_id,
                "configuration": {
                    "max_tlp": 3,
                    "max_pap": 3,
                    "check_tlp": False,
                    "check_pap": False,
                    "auto_extract_artifacts": False,
                },
            },
            verify=False,
            timeout=60,
        )
        if resp.status_code in (200, 201, 409):
            return True
        logger.warning(
            "[cortex] Could not install %s: HTTP %d %s",
            definition_id,
            resp.status_code,
            resp.text[:120],
        )
        return False
    except Exception as _install_e:
        logger.warning("[cortex] Could not install %s: %s", definition_id, _install_e)
        return False


def discover_and_select_analyzers(cortex_basic: str, app_id_http: str) -> dict[str, Any]:
    """Discover installed analyzers, install missing wanted ones, and select
    IDs.

    Returns a dict with the selected analyzer IDs and availability
    flags, suitable for constructing a :class:`WorkflowContext`.
    """
    hash_analyzer_id = "Hashdd_Status"
    ip_analyzer_id = "IP-API"
    hash_virusshare_id = "Virusshare_2_0"
    ip_dshield_id = "DShield_lookup"
    ip_mnemonic_pdns_id = "Mnemonic_pDNS_Public"
    ip_googledns_id = "GoogleDNS_resolve"
    ip_ipapi_id = "IP-API"
    has_hash_virusshare = False
    has_ip_dshield = False
    has_ip_mnemonic_pdns = False
    has_ip_googledns = False
    has_ip_ipapi = False

    hash_ans: list[dict] = []
    ip_ans: list[dict] = []
    all_analyzers: list[dict] = []

    try:
        client = _build_cortex_client(cortex_basic)
        if client is not None:
            all_analyzers = client.list_analyzers()
            installed_names = {a.get("name", "") for a in all_analyzers}
            missing_wanted = [n for n in _WANTED_ANALYZERS if n not in installed_names]
            if missing_wanted:
                defs = client.list_analyzer_definitions()
                def_by_name = {d.get("id") or d.get("name"): d for d in defs}
                any_installed = False
                for name in missing_wanted:
                    if name in def_by_name and _cortex_install_analyzer(name, cortex_basic):
                        logger.info("[cortex] Installed missing analyzer: %s", name)
                        any_installed = True
                    else:
                        logger.warning(
                            "[cortex] Analyzer not available in catalog, skipping: %s", name
                        )
                if any_installed:
                    all_analyzers = client.list_analyzers()
        else:
            # Fallback: raw requests
            import requests

            analyzers_r = requests.get(
                f"{config.CORTEX_URL}/api/analyzer",
                headers={HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {cortex_basic}"},
                verify=False,
                timeout=30,
            )
            if analyzers_r.ok:
                all_analyzers = analyzers_r.json() if isinstance(analyzers_r.json(), list) else []
                installed_names = {a.get("name", "") for a in all_analyzers}
                missing_wanted = [n for n in _WANTED_ANALYZERS if n not in installed_names]
                if missing_wanted:
                    defs_r = requests.get(
                        f"{config.CORTEX_URL}/api/analyzerdefinition",
                        headers={HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {cortex_basic}"},
                        verify=False,
                        timeout=30,
                    )
                    defs = defs_r.json() if defs_r.ok and isinstance(defs_r.json(), list) else []
                    def_by_name = {d.get("id") or d.get("name"): d for d in defs}
                    any_installed = False
                    for name in missing_wanted:
                        if name in def_by_name and _cortex_install_analyzer(name, cortex_basic):
                            logger.info("[cortex] Installed missing analyzer: %s", name)
                            any_installed = True
                        else:
                            logger.warning(
                                "[cortex] Analyzer not available in catalog, skipping: %s", name
                            )
                    if any_installed:
                        analyzers_r = requests.get(
                            f"{config.CORTEX_URL}/api/analyzer",
                            headers={HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {cortex_basic}"},
                            verify=False,
                            timeout=30,
                        )
                        all_analyzers = (
                            analyzers_r.json()
                            if analyzers_r.ok and isinstance(analyzers_r.json(), list)
                            else all_analyzers
                        )

        # ── Common selection logic (runs for both CortexClient and fallback) ──
        logger.info("[cortex] Total analyzers available: %d", len(all_analyzers))
        hash_ans = [a for a in all_analyzers if "hash" in a.get("dataTypeList", [])]
        ip_ans = [a for a in all_analyzers if "ip" in a.get("dataTypeList", [])]
        domain_ans = [a for a in all_analyzers if "domain" in a.get("dataTypeList", [])]
        url_ans = [a for a in all_analyzers if "url" in a.get("dataTypeList", [])]
        file_ans = [a for a in all_analyzers if "file" in a.get("dataTypeList", [])]
        logger.info(
            "[cortex] Hash analyzers (%d): %s", len(hash_ans), [a["name"] for a in hash_ans]
        )
        logger.info("[cortex] IP analyzers (%d): %s", len(ip_ans), [a["name"] for a in ip_ans])
        logger.info(
            "[cortex] Domain analyzers (%d): %s", len(domain_ans), [a["name"] for a in domain_ans]
        )
        logger.info("[cortex] URL analyzers (%d): %s", len(url_ans), [a["name"] for a in url_ans])
        logger.info(
            "[cortex] File analyzers (%d): %s", len(file_ans), [a["name"] for a in file_ans]
        )

        def _get_id(a):
            return a.get("id") or a.get("_id") or a["name"]

        def _find_preferred(analyzers: list[dict], wanted_names: list[str]) -> dict | None:
            """Find the first analyzer whose name matches one of the wanted
            names."""
            for wanted in wanted_names:
                for a in analyzers:
                    if wanted in a.get("name", ""):
                        return a
            return None

        # Prefer Hashdd_Status for hash, IP-API for IP (from _WANTED_ANALYZERS).
        # Fall back to the first available analyzer of each type.
        preferred_hash = _find_preferred(hash_ans, ["Hashdd_Status", "Virusshare"])
        if preferred_hash:
            hash_analyzer_id = _get_id(preferred_hash)
        elif hash_ans:
            hash_analyzer_id = _get_id(hash_ans[0])
        logger.info("[cortex] Selected hash analyzer: %s", hash_analyzer_id)

        preferred_ip = _find_preferred(ip_ans, ["IP-API", "DShield_lookup"])
        if preferred_ip:
            ip_analyzer_id = _get_id(preferred_ip)
        elif ip_ans:
            ip_analyzer_id = _get_id(ip_ans[0])
        logger.info("[cortex] Selected IP analyzer: %s", ip_analyzer_id)
        virusshare = [a for a in hash_ans if "Virusshare" in a["name"]]
        if virusshare:
            hash_virusshare_id = _get_id(virusshare[0])
            has_hash_virusshare = True
            logger.info("[cortex] Selected Virusshare analyzer: %s", hash_virusshare_id)
        dshield = [a for a in ip_ans if "DShield_lookup" in a["name"]]
        if dshield:
            ip_dshield_id = _get_id(dshield[0])
            has_ip_dshield = True
            logger.info("[cortex] Selected DShield analyzer: %s", ip_dshield_id)
        mnemonic_pdns = [a for a in ip_ans if "Mnemonic_pDNS_Public" in a["name"]]
        if mnemonic_pdns:
            ip_mnemonic_pdns_id = _get_id(mnemonic_pdns[0])
            has_ip_mnemonic_pdns = True
            logger.info("[cortex] Selected Mnemonic pDNS analyzer: %s", ip_mnemonic_pdns_id)
        googledns = [a for a in ip_ans if "GoogleDNS_resolve" in a["name"]]
        if googledns:
            ip_googledns_id = _get_id(googledns[0])
            has_ip_googledns = True
            logger.info("[cortex] Selected GoogleDNS analyzer: %s", ip_googledns_id)
        ipapi = [a for a in ip_ans if "IP-API" in a["name"]]
        if ipapi:
            ip_ipapi_id = _get_id(ipapi[0])
            has_ip_ipapi = True
            logger.info("[cortex] Selected IP-API analyzer: %s", ip_ipapi_id)
    except Exception as _e:
        logger.warning("[cortex] WARN could not get analyzers: %s", _e)

    # Dynamically wire any remaining *installed* Cortex analyzer
    dynamic_cortex_actions: list[dict[str, Any]] = []
    dynamic_cortex_branches: list[dict[str, Any]] = []
    try:
        wired_names = {
            "Virusshare",
            "DShield_lookup",
            "Mnemonic_pDNS_Public",
            "IP-API",
            "GoogleDNS_resolve",
        }
        if hash_ans:
            wired_names.add(hash_ans[0]["name"])
        if ip_ans:
            wired_names.add(ip_ans[0]["name"])
        dyn_pos_y = -260
        for a in all_analyzers:
            name = a.get("name", "")
            if not name or name in wired_names or name in _SKIP_DYNAMIC_NAMES:
                continue
            dtypes = a.get("dataTypeList", [])
            if "domain" in dtypes:
                field, dtype_label = "$exec.domain", "domain"
            elif "url" in dtypes:
                field, dtype_label = "$exec.url", "url"
            elif "hash" in dtypes or "file" in dtypes:
                field, dtype_label = "$exec.hash", "hash"
            elif "ip" in dtypes:
                field, dtype_label = "$exec.src_ip", "ip"
            else:
                continue
            wired_names.add(name)
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            aid = f"act_cortex_dyn_{slug}"
            dyn_pos_y += 40

            def _get_id(a_item):
                return a_item.get("id") or a_item.get("_id") or a_item["name"]

            dynamic_cortex_actions.append(
                action(
                    aid=aid,
                    name=f"cortex_dyn_{slug}",
                    app_name="http",
                    app_version="1.0.0",
                    app_id=app_id_http,
                    action_name="POST",
                    params=[
                        param("url", f"{config.CORTEX_INT}/api/analyzer/{_get_id(a)}/run"),
                        param(
                            "headers",
                            "Content-Type: application/json\nAuthorization: Basic " + cortex_basic,
                        ),
                        param(
                            "body",
                            f'{{"data": "{field}",'
                            f' "attributes": {{"dataType": "{dtype_label}", "tlp": 2}}}}',
                        ),
                        param("timeout", "120"),
                    ],
                    position=pos(950, dyn_pos_y),
                )
            )
            dynamic_cortex_branches.append(branch(f"br_hive_cortex_dyn_{slug}", ACT_THEHIVE, aid))
            dynamic_cortex_branches.append(
                branch(f"br_cortex_dyn_{slug}_decision", aid, ACT_CALC_DECISION)
            )
        if dynamic_cortex_actions:
            logger.info(
                "  [cortex] Dynamically wired %d additional installed analyzer(s): %s",
                len(dynamic_cortex_actions),
                [a["label"] for a in dynamic_cortex_actions],
            )
    except Exception as _dyn_e:
        logger.warning("[cortex] WARN could not build dynamic analyzer nodes: %s", _dyn_e)

    return {
        "hash_analyzer_id": hash_analyzer_id,
        "ip_analyzer_id": ip_analyzer_id,
        "hash_virusshare_id": hash_virusshare_id,
        "ip_dshield_id": ip_dshield_id,
        "ip_mnemonic_pdns_id": ip_mnemonic_pdns_id,
        "ip_googledns_id": ip_googledns_id,
        "ip_ipapi_id": ip_ipapi_id,
        "has_hash_virusshare": has_hash_virusshare,
        "has_ip_dshield": has_ip_dshield,
        "has_ip_mnemonic_pdns": has_ip_mnemonic_pdns,
        "has_ip_googledns": has_ip_googledns,
        "has_ip_ipapi": has_ip_ipapi,
        "dynamic_cortex_actions": dynamic_cortex_actions,
        "dynamic_cortex_branches": dynamic_cortex_branches,
    }
