"""BUG-072 regression: skipped/wired Cortex analyzer names must dedupe by
base name, not exact name.

Installed analyzer instances carry version-suffixed names
(``GoogleDNS_resolve_1_0_0``, ``Robtex_Reverse_PDNS_Query_1_0``) while the
wired- and skip-lists in ``cortex_setup.py`` use base names. Exact-string
matching let skipped analyzers get dynamically wired anyway — the deployed
workflow ran ``Robtex_Reverse_PDNS_Query``, ``MaxMind_GeoIP`` and
``Crt_sh_Transparency_Logs`` on every alert (~107 failures/hour, KPI-06).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.setup.shuffle_workflow import cortex_setup


def _base_name(n: str) -> str:
    return re.sub(r"_\d+(?:_\d+)*$", "", n)


class TestAnalyzerNameDedup:
    def test_skip_list_covers_versioned_names(self):
        """Every skip entry must match its deployed versioned instance name
        after base-name normalization."""
        deployed = [
            "Robtex_Reverse_PDNS_Query",
            "Robtex_IP_Query",
            "Robtex_Forward_PDNS_Query",
            "MaxMind_GeoIP",
            "Crt_sh_Transparency_Logs",
            "GoogleDNS_resolve_1_0_0",
            "Virusshare_2_0",
        ]
        skip_bases = {_base_name(n) for n in cortex_setup._SKIP_DYNAMIC_NAMES}
        wired_bases = {
            _base_name(n)
            for n in (
                "Virusshare",
                "DShield_lookup",
                "Mnemonic_pDNS_Public",
                "IP-API",
                "GoogleDNS_resolve",
            )
        }
        for name in deployed:
            base = _base_name(name)
            covered = base in skip_bases or base in wired_bases
            assert covered, (
                f"{name} (base {base}) is neither wired nor skipped — "
                "it would be dynamically wired and run on every alert"
            )

    def test_dedup_uses_base_name_matching(self):
        """The dedup loop must normalize names before comparing, not only
        use exact-string membership."""
        src = Path(cortex_setup.__file__).read_text(encoding="utf-8")
        assert "_base_name" in src, (
            "cortex_setup lost base-name normalization — versioned "
            "analyzer names would bypass _SKIP_DYNAMIC_NAMES again"
        )
        assert "wired_bases" in src and "skip_bases" in src
