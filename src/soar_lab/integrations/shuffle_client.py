"""Backward-compatibility shim for the ShuffleClient integration client."""

import threading
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient

__all__ = ["ShuffleClient", "threading"]
