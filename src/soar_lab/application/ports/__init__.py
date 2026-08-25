"""Application ports package - input and output port definitions.

This package contains the port definitions for the hexagonal architecture:
- ``input``: use case interfaces that input adapters (HTTP, CLI) depend on.
- ``output``: infrastructure contracts that use cases depend on, re-exported
  from ``domain.ports`` to maintain the dependency direction.
"""
