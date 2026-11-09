"""Declarative adapter registry for external integrations (A2).

Adding a SOAR integration used to mean editing the composition root in
several places: import the client, add a constructor call, add an
attribute, add the health-service map entry. The registry collapses
that into one declared row — a new adapter registers a
:class:`AdapterSpec` and the composition root builds the whole set.

The composition root stays the only place adapters are *instantiated*;
this module only describes *how* to build them.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from soar_lab.common.constants import (
    SERVICE_CORTEX,
    SERVICE_ELASTICSEARCH,
    SERVICE_MISP,
    SERVICE_SHUFFLE,
    SERVICE_THEHIVE,
)
from soar_lab.infrastructure.integrations.cortex.client import CortexClient
from soar_lab.infrastructure.integrations.elasticsearch.client import ElasticsearchClient
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient

__all__ = ["AdapterSpec", "INTEGRATION_ADAPTERS", "build_integration_clients"]


@dataclass(frozen=True)
class AdapterSpec:
    """How to construct one external-service adapter.

    Attributes:
        name: Service key (``SERVICE_*`` constant); the composition root
            exposes the instance as ``<name>_client``.
        url_key: Config key holding the service base URL.
        api_key_key: Config key holding the API key, or ``None`` when the
            service authenticates differently (e.g. Elasticsearch).
        factory: ``(base_url, api_key, config_provider) -> client``.
    """

    name: str
    url_key: str
    api_key_key: str | None
    factory: Callable[[Any, Any, Any], Any]

    def build(self, config_provider: Any) -> Any:
        """Instantiate the adapter from resolved config values."""
        base_url = config_provider.get(self.url_key)
        api_key = config_provider.get(self.api_key_key) if self.api_key_key else None
        return self.factory(base_url, api_key, config_provider)


def _keyed(cls: type) -> Callable[[Any, Any, Any], Any]:
    """Adapter factory for clients taking ``(base_url, api_key, cp)``."""

    def _build(base_url: Any, api_key: Any, cp: Any) -> Any:
        return cls(base_url=base_url, api_key=api_key, config_provider=cp)

    return _build


INTEGRATION_ADAPTERS: tuple[AdapterSpec, ...] = (
    AdapterSpec(SERVICE_CORTEX, "cortex_url", "cortex_api_key", _keyed(CortexClient)),
    AdapterSpec(SERVICE_SHUFFLE, "shuffle_url", "shuffle_api_key", _keyed(ShuffleClient)),
    AdapterSpec(SERVICE_THEHIVE, "thehive_url", "thehive_api_key", _keyed(TheHiveClient)),
    AdapterSpec(SERVICE_MISP, "misp_url", "misp_api_key", _keyed(MISPClient)),
    AdapterSpec(
        SERVICE_ELASTICSEARCH,
        "elasticsearch_url",
        None,
        lambda base_url, _key, cp: ElasticsearchClient(base_url=base_url, config_provider=cp),
    ),
)


def build_integration_clients(config_provider: Any) -> dict[str, Any]:
    """Instantiate every registered adapter; ``{service_name: client}``."""
    return {spec.name: spec.build(config_provider) for spec in INTEGRATION_ADAPTERS}
