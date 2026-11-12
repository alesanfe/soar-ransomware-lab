#!/usr/bin/env python3
"""Eager-init branch: importing without SOAR_SKIP_EAGER_INIT calls create_app."""

import importlib
import sys
from unittest.mock import patch


def test_eager_init_calls_create_app():
    import soar_lab.interfaces.api as pkg

    sentinel = object()
    with (
        patch.dict("os.environ", {"SOAR_SKIP_EAGER_INIT": "0"}),
        patch(
            "soar_lab.interfaces.api.composition.create_app",
            return_value=sentinel,
        ) as ca,
    ):
        # composition.create_app must be re-bound inside the package too —
        # the module imported it by name at load time, so patch the local ref.
        import soar_lab.interfaces.api.composition as comp

        with patch.object(comp, "create_app", return_value=sentinel):
            pkg = importlib.reload(pkg)
    try:
        assert pkg.app is sentinel
    finally:
        # Restore skip-eager state for the rest of the suite.
        with patch.dict("os.environ", {"SOAR_SKIP_EAGER_INIT": "1"}):
            importlib.reload(pkg)
