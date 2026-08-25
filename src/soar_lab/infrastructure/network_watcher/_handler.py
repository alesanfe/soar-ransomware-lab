"""HTTP handler for the network watcher's REST API."""

import ipaddress
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import docker

try:
    from soar_lab.infrastructure.network_watcher._constants import (
        CONTENT_TYPE_JSON,
        HEADER_CONTENT_TYPE,
        TARGET_NETWORK,
    )
except ImportError:
    from _constants import (  # type: ignore[no-redef]
        CONTENT_TYPE_JSON,
        HEADER_CONTENT_TYPE,
        TARGET_NETWORK,
    )

__all__ = ["create_handler"]


def create_handler(client: docker.DockerClient) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP request handler class bound to the given Docker client.

    Args:
        client: Docker client instance used for network queries.

    Returns:
        A Handler class for use with ``ThreadingHTTPServer``.
    """

    class Handler(BaseHTTPRequestHandler):
        """HTTP handler exposing health and connection inspection endpoints."""

        def _write_json(self, status: int, body: dict) -> None:
            """Write a JSON response with the given status code and body."""
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header(HEADER_CONTENT_TYPE, CONTENT_TYPE_JSON)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _handle_health(self) -> None:
            """Handle the ``/health`` endpoint."""
            try:
                network = client.networks.get(TARGET_NETWORK)
                self._write_json(200, {"status": "ok", "network": network.name})
            except docker.errors.NotFound:
                self._write_json(503, {"status": "unavailable", "network": TARGET_NETWORK})

        def _handle_connections(self, parsed) -> None:
            """Handle the ``/api/connections`` endpoint."""
            query = parse_qs(parsed.query)
            raw_limit = query.get("limit", ["100"])[0]
            requested_ip = query.get("ip", [None])[0]
            try:
                limit = int(raw_limit)
                if not 1 <= limit <= 1000:
                    raise ValueError
                if requested_ip is not None:
                    ipaddress.ip_address(requested_ip)
            except ValueError:
                self._write_json(
                    400,
                    {"error": ("ip must be a valid address and limit must be between 1 and 1000")},
                )
                return
            try:
                containers = client.networks.get(TARGET_NETWORK).attrs.get("Containers") or {}
                connections = [
                    {
                        "id": container_id,
                        "name": container.get("Name", ""),
                        "ip": container.get("IPv4Address", "").split("/")[0],
                        "endpoint_id": container.get("EndpointID", ""),
                    }
                    for container_id, container in containers.items()
                ]
                if requested_ip is not None:
                    connections = [
                        connection for connection in connections if connection["ip"] == requested_ip
                    ]
                self._write_json(
                    200,
                    {
                        "network": TARGET_NETWORK,
                        "total": len(connections),
                        "connections": connections[:limit],
                    },
                )
            except docker.errors.NotFound:
                self._write_json(503, {"error": f"network {TARGET_NETWORK} is unavailable"})

        def _handle_connection_detail(self, parsed) -> None:
            """Handle the ``/api/connections/<id>`` endpoint."""
            prefix = "/api/connections/"
            connection_id = parsed.path[len(prefix) :]
            try:
                containers = client.networks.get(TARGET_NETWORK).attrs.get("Containers") or {}
                container = containers.get(connection_id)
                if container is None:
                    self._write_json(404, {"error": "connection not found"})
                else:
                    self._write_json(
                        200,
                        {
                            "id": connection_id,
                            "name": container.get("Name", ""),
                            "ip": container.get("IPv4Address", "").split("/")[0],
                            "endpoint_id": container.get("EndpointID", ""),
                            "network": TARGET_NETWORK,
                        },
                    )
            except docker.errors.NotFound:
                self._write_json(503, {"error": f"network {TARGET_NETWORK} is unavailable"})

        def do_GET(self) -> None:
            """Handle GET requests for health and connection inspection."""
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._handle_health()
                return
            if parsed.path == "/api/connections":
                self._handle_connections(parsed)
                return
            if parsed.path.startswith("/api/connections/"):
                self._handle_connection_detail(parsed)
                return
            self._write_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            """Suppress default request logging."""
            return

    return Handler
