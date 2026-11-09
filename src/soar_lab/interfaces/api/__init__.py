"""FastAPI application package — single composition root.

There is exactly one wiring: ``interfaces/api/composition.py``'s
``CompositionRoot`` (used by the Dockerfile CMD and the ``soar-lab api``
CLI). This module delegates to it so ``uvicorn
soar_lab.interfaces.api:app`` resolves the SAME application instead of a
parallel, dependency-starved wiring.

Tests can skip eager instantiation entirely with ``SOAR_SKIP_EAGER_INIT``
— importing this package then performs no I/O, no client construction and
no settings resolution.
"""

import os

from .composition import create_app  # re-export for --factory users

_SKIP_EAGER_INIT = os.getenv("SOAR_SKIP_EAGER_INIT", "").lower() in ("1", "true", "yes")

if _SKIP_EAGER_INIT:
    app = None
else:
    # Single wiring path — identical to `composition:create_app --factory`.
    app = create_app()

__all__ = ["app", "create_app"]
