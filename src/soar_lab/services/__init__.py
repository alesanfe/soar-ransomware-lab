"""Compatibility shim: expose old `soar_lab.services.*` module names."""
import importlib
import sys


def _alias(name: str, target: str):
    """Map `soar_lab.services.<name>` to the same module object as `target`."""
    try:
        mod = importlib.import_module(target)
    except ModuleNotFoundError:
        return
    sys.modules[f"soar_lab.services.{name}"] = mod
    return mod


# Redirect deprecated service paths to their current canonical locations.
_alias("analytics_service", "soar_lab.application.use_cases.analytics_service")
_alias("generate_kpi_data", "soar_lab.scripts.generate_kpi_data")
_alias("send_to_both_workflows", "soar_lab.scripts.send_to_both_workflows")
