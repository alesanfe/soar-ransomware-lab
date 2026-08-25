#!/usr/bin/env python3
"""Unit tests for infrastructure.network_watcher.network_watcher module.

Tests the Docker network watcher helper functions and HTTP handler using
mocked Docker clients and containers.
"""

import io
import tarfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from soar_lab.infrastructure.network_watcher import network_watcher as nw

__all__ = [
    "TestIsShuffleContainer",
    "TestGetIp",
    "TestInjectHosts",
    "TestSetupDockerSocket",
    "TestFixResolv",
    "TestAttach",
    "TestInjectHostsFile",
    "TestCreateHandler",
    "TestStartHttpServer",
]


class TestIsShuffleContainer:
    """Tests for is_shuffle_container function."""

    def test_worker_prefix(self):
        """Test that names starting with 'worker-' are identified as Shuffle containers."""
        assert nw.is_shuffle_container("worker-abc123") is True

    def test_http_prefix(self):
        """Test that names starting with 'HTTP_' are identified as Shuffle containers."""
        assert nw.is_shuffle_container("HTTP_app1") is True

    def test_act_in_name(self):
        """Test that names containing '_act_' are identified as Shuffle containers."""
        assert nw.is_shuffle_container("container_act_test") is True

    def test_non_shuffle_name(self):
        """Test that regular container names are not identified as Shuffle containers."""
        assert nw.is_shuffle_container("nginx") is False

    def test_empty_string(self):
        """Test that empty string is not a Shuffle container."""
        assert nw.is_shuffle_container("") is False


class TestGetIp:
    """Tests for get_ip function."""

    def test_get_ip_success(self):
        """Test successful retrieval of container IP address."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "NetworkSettings": {"Networks": {"soar_net": {"IPAddress": "172.18.0.5"}}}
        }
        mock_client.containers.get.return_value = mock_container

        result = nw.get_ip(mock_client, "thehive", "soar_net")
        assert result == "172.18.0.5"

    def test_get_ip_no_network(self):
        """Test that empty string is returned when container is not on the network."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.attrs = {"NetworkSettings": {"Networks": {}}}
        mock_client.containers.get.return_value = mock_container

        result = nw.get_ip(mock_client, "thehive", "soar_net")
        assert result == ""

    def test_get_ip_container_not_found(self):
        """Test that empty string is returned when container does not exist."""
        mock_client = Mock()
        mock_client.containers.get.side_effect = Exception("Not found")

        result = nw.get_ip(mock_client, "nonexistent", "soar_net")
        assert result == ""


class TestInjectHosts:
    """Tests for inject_hosts function."""

    def test_inject_hosts_success(self):
        """Test that hosts entries are injected when IPs are found."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"

        def fake_get_ip(client, cname, network):
            if "thehive" in cname:
                return "172.18.0.2"
            return ""

        with patch.object(nw, "get_ip", side_effect=fake_get_ip):
            nw.inject_hosts(mock_container, mock_client, "soar_net")

        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args
        assert call_args[1]["user"] == "root"

    def test_inject_hosts_no_ips_found(self):
        """Test that no exec_run is called when no IPs are found."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"

        with patch.object(nw, "get_ip", return_value=""):
            nw.inject_hosts(mock_container, mock_client, "soar_net")

        mock_container.exec_run.assert_not_called()

    def test_inject_hosts_exception_handled(self):
        """Test that exceptions during host injection are caught and logged."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"
        mock_container.exec_run.side_effect = Exception("exec failed")

        with patch.object(nw, "get_ip", return_value="172.18.0.2"):
            # Should not raise
            nw.inject_hosts(mock_container, mock_client, "soar_net")


class TestSetupDockerSocket:
    """Tests for setup_docker_socket function."""

    def test_setup_docker_socket_socat_not_found(self):
        """Test that setup is skipped when socat binary does not exist."""
        mock_container = Mock()
        mock_container.name = "worker-1"

        with (
            patch("os.path.exists", return_value=False),
            patch("os.path.isfile", return_value=False),
        ):
            nw.setup_docker_socket(mock_container)

        mock_container.put_archive.assert_not_called()
        mock_container.exec_run.assert_not_called()

    def test_setup_docker_socket_success(self):
        """Test successful Docker socket forwarding setup."""
        mock_container = Mock()
        mock_container.name = "worker-1"

        mock_tf = MagicMock()
        mock_tf.__enter__ = Mock(return_value=mock_tf)
        mock_tf.__exit__ = Mock(return_value=False)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.isfile", return_value=True),
            patch("tarfile.open", return_value=mock_tf),
        ):
            nw.setup_docker_socket(mock_container)

        mock_container.put_archive.assert_called_once()
        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args
        assert call_args[1]["user"] == "root"
        assert call_args[1]["detach"] is True

    def test_setup_docker_socket_exception_handled(self):
        """Test that exceptions during socket setup are caught and logged."""
        mock_container = Mock()
        mock_container.name = "worker-1"
        mock_container.put_archive.side_effect = Exception("put failed")

        mock_tf = MagicMock()
        mock_tf.__enter__ = Mock(return_value=mock_tf)
        mock_tf.__exit__ = Mock(return_value=False)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.isfile", return_value=True),
            patch("tarfile.open", return_value=mock_tf),
        ):
            # Should not raise
            nw.setup_docker_socket(mock_container)


class TestFixResolv:
    """Tests for fix_resolv function."""

    def test_fix_resolv_success(self):
        """Test that resolv.conf is rewritten successfully."""
        mock_container = Mock()
        mock_container.name = "worker-1"

        nw.fix_resolv(mock_container, "soar_net")

        mock_container.exec_run.assert_called_once()
        call_args = mock_container.exec_run.call_args
        assert call_args[1]["user"] == "root"
        assert "nameserver 127.0.0.11" in call_args[0][0][2]

    def test_fix_resolv_exception_handled(self):
        """Test that exceptions during resolv.conf fix are caught and logged."""
        mock_container = Mock()
        mock_container.name = "worker-1"
        mock_container.exec_run.side_effect = Exception("exec failed")

        # Should not raise
        nw.fix_resolv(mock_container, "soar_net")


class TestAttach:
    """Tests for attach function."""

    def test_attach_container_mode_skip(self):
        """Test that containers with 'container:' network mode are skipped for network connect."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "HostConfig": {"NetworkMode": "container:orborus"},
            "NetworkSettings": {"Networks": {}},
        }
        mock_container.status = "running"
        mock_container.name = "worker-1"
        mock_client.containers.get.return_value = mock_container

        with (
            patch.object(nw.threading, "Thread") as mock_thread_cls,
            patch.object(nw, "is_shuffle_container", return_value=True),
        ):
            mock_thread = Mock()
            mock_thread_cls.return_value = mock_thread

            nw.attach(mock_client, "cid123", "worker-1", "soar_net")

        # Network connect should NOT be called for container: mode
        mock_client.networks.get.return_value.connect.assert_not_called()

    def test_attach_connects_to_network(self):
        """Test that container is connected to the target network when not already connected."""
        mock_client = Mock()
        mock_net = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "HostConfig": {"NetworkMode": "default"},
            "NetworkSettings": {"Networks": {"bridge": {}}},
        }
        mock_container.name = "worker-1"
        mock_client.networks.get.return_value = mock_net
        mock_client.containers.get.return_value = mock_container

        with patch.object(nw, "is_shuffle_container", return_value=False):
            nw.attach(mock_client, "cid123", "regular-container", "soar_net")

        mock_net.connect.assert_called_once_with(mock_container)

    def test_attach_already_connected(self):
        """Test that network connect is skipped when container is already on the network."""
        mock_client = Mock()
        mock_net = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "HostConfig": {"NetworkMode": "default"},
            "NetworkSettings": {"Networks": {"soar_net": {}}},
        }
        mock_container.name = "regular-container"
        mock_client.networks.get.return_value = mock_net
        mock_client.containers.get.return_value = mock_container

        with patch.object(nw, "is_shuffle_container", return_value=False):
            nw.attach(mock_client, "cid123", "regular-container", "soar_net")

        mock_net.connect.assert_not_called()

    def test_attach_shuffle_container_running(self):
        """Test that hosts are injected for running Shuffle containers."""
        mock_client = Mock()
        mock_net = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "HostConfig": {"NetworkMode": "default"},
            "NetworkSettings": {"Networks": {}},
        }
        mock_container.status = "running"
        mock_container.name = "worker-1"
        mock_client.networks.get.return_value = mock_net
        mock_client.containers.get.return_value = mock_container

        with (
            patch.object(nw, "is_shuffle_container", return_value=True),
            patch.object(nw.threading, "Thread") as mock_thread_cls,
        ):
            mock_thread = Mock()
            mock_thread_cls.return_value = mock_thread

            nw.attach(mock_client, "cid123", "worker-1", "soar_net")

        # Should start threads for fix_resolv, inject_hosts, setup_docker_socket
        assert mock_thread_cls.call_count == 3

    def test_attach_shuffle_container_create_action(self):
        """Test that hosts file is pre-injected for Shuffle containers on create action."""
        mock_client = Mock()
        mock_net = Mock()
        mock_container = Mock()
        mock_container.attrs = {
            "HostConfig": {"NetworkMode": "default"},
            "NetworkSettings": {"Networks": {}},
        }
        mock_container.status = "created"
        mock_container.name = "HTTP_app1"
        mock_client.networks.get.return_value = mock_net
        mock_client.containers.get.return_value = mock_container

        with (
            patch.object(nw, "is_shuffle_container", return_value=True),
            patch.object(nw.threading, "Thread") as mock_thread_cls,
        ):
            mock_thread = Mock()
            mock_thread_cls.return_value = mock_thread

            nw.attach(mock_client, "cid123", "HTTP_app1", "soar_net", action="create")

        # Should start one thread for inject_hosts_file
        assert mock_thread_cls.call_count == 1

    def test_attach_exception_handled(self):
        """Test that exceptions during attach are caught and logged."""
        mock_client = Mock()
        mock_client.networks.get.side_effect = Exception("network error")

        # Should not raise
        nw.attach(mock_client, "cid123", "worker-1", "soar_net")


class TestInjectHostsFile:
    """Tests for inject_hosts_file function."""

    def test_inject_hosts_file_no_ips(self):
        """Test that function returns early when no IPs are found."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"

        with patch.object(nw, "get_ip", return_value=""):
            nw.inject_hosts_file(mock_container, mock_client, "soar_net")

        mock_container.get_archive.assert_not_called()

    def test_inject_hosts_file_success(self):
        """Test successful hosts file injection via tar archive."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"

        # Create a tar archive for the existing /etc/hosts content
        existing_buf = io.BytesIO()
        with tarfile.open(fileobj=existing_buf, mode="w") as tf:
            data = b"127.0.0.1 localhost\n"
            info = tarfile.TarInfo(name="hosts")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        existing_bytes = existing_buf.getvalue()

        # get_archive returns (bits, stat) where bits is an iterable of bytes chunks
        mock_container.get_archive.return_value = ([existing_bytes], None)

        with patch.object(nw, "get_ip", return_value="172.18.0.2"):
            nw.inject_hosts_file(mock_container, mock_client, "soar_net")

        mock_container.put_archive.assert_called_once()

    def test_inject_hosts_file_retries_on_error(self):
        """Test that function retries on error up to max_retries."""
        mock_client = Mock()
        mock_container = Mock()
        mock_container.name = "worker-1"
        mock_container.get_archive.side_effect = Exception("not ready")

        with (
            patch.object(nw, "get_ip", return_value="172.18.0.2"),
            patch("time.sleep"),
        ):
            nw.inject_hosts_file(mock_container, mock_client, "soar_net")

        # Should have retried max_retries times (5)
        assert mock_container.get_archive.call_count == 5


def _make_handler_instance(Handler, path="/health"):
    """Create a handler instance without going through BaseHTTPRequestHandler.__init__.

    BaseHTTPRequestHandler.__init__ tries to read from a socket, which we
    don't want in unit tests. We bypass it by calling __new__ and setting
    the attributes we need manually.
    """
    handler = Handler.__new__(Handler)
    handler.path = path
    handler._write_json = Mock()
    return handler


class TestCreateHandler:
    """Tests for create_handler and the HTTP handler."""

    def test_health_endpoint_ok(self):
        """Test /health endpoint returns 200 when network exists."""
        mock_client = Mock()
        mock_network = Mock()
        mock_network.name = "soar_net"
        mock_client.networks.get.return_value = mock_network

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/health")

        handler.do_GET()

        handler._write_json.assert_called_once_with(200, {"status": "ok", "network": "soar_net"})

    def test_health_endpoint_network_not_found(self):
        """Test /health endpoint returns 503 when network does not exist."""
        mock_client = Mock()
        mock_client.networks.get.side_effect = nw.docker.errors.NotFound("not found")

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/health")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 503
        assert call_args[1]["status"] == "unavailable"

    def test_connections_list(self):
        """Test /api/connections endpoint returns list of connections."""
        mock_client = Mock()
        mock_network = Mock()
        mock_network.attrs = {
            "Containers": {
                "cid1": {"Name": "worker-1", "IPv4Address": "172.18.0.2/24", "EndpointID": "eid1"},
                "cid2": {"Name": "thehive", "IPv4Address": "172.18.0.3/24", "EndpointID": "eid2"},
            }
        }
        mock_client.networks.get.return_value = mock_network

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections?limit=10")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 200
        assert call_args[1]["total"] == 2
        assert len(call_args[1]["connections"]) == 2

    def test_connections_invalid_limit(self):
        """Test /api/connections returns 400 for invalid limit."""
        mock_client = Mock()
        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections?limit=9999")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 400

    def test_connections_invalid_ip(self):
        """Test /api/connections returns 400 for invalid IP address."""
        mock_client = Mock()
        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections?ip=not-an-ip")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 400

    def test_connections_filter_by_ip(self):
        """Test /api/connections filters by IP address."""
        mock_client = Mock()
        mock_network = Mock()
        mock_network.attrs = {
            "Containers": {
                "cid1": {"Name": "worker-1", "IPv4Address": "172.18.0.2/24", "EndpointID": "eid1"},
                "cid2": {"Name": "thehive", "IPv4Address": "172.18.0.3/24", "EndpointID": "eid2"},
            }
        }
        mock_client.networks.get.return_value = mock_network

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections?ip=172.18.0.2")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 200
        assert call_args[1]["total"] == 1
        assert call_args[1]["connections"][0]["ip"] == "172.18.0.2"

    def test_connection_by_id_found(self):
        """Test /api/connections/{id} returns connection details."""
        mock_client = Mock()
        mock_network = Mock()
        mock_network.attrs = {
            "Containers": {
                "cid1": {"Name": "worker-1", "IPv4Address": "172.18.0.2/24", "EndpointID": "eid1"},
            }
        }
        mock_client.networks.get.return_value = mock_network

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections/cid1")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 200
        assert call_args[1]["id"] == "cid1"
        assert call_args[1]["name"] == "worker-1"

    def test_connection_by_id_not_found(self):
        """Test /api/connections/{id} returns 404 for unknown connection."""
        mock_client = Mock()
        mock_network = Mock()
        mock_network.attrs = {"Containers": {}}
        mock_client.networks.get.return_value = mock_network

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections/unknown")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 404

    def test_connection_by_id_network_not_found(self):
        """Test /api/connections/{id} returns 503 when network is unavailable."""
        mock_client = Mock()
        mock_client.networks.get.side_effect = nw.docker.errors.NotFound("not found")

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections/cid1")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 503

    def test_connections_network_not_found(self):
        """Test /api/connections returns 503 when network is unavailable."""
        mock_client = Mock()
        mock_client.networks.get.side_effect = nw.docker.errors.NotFound("not found")

        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/api/connections")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 503

    def test_unknown_path_returns_404(self):
        """Test that unknown paths return 404."""
        mock_client = Mock()
        Handler = nw.create_handler(mock_client)
        handler = _make_handler_instance(Handler, path="/unknown")

        handler.do_GET()

        handler._write_json.assert_called_once()
        call_args = handler._write_json.call_args[0]
        assert call_args[0] == 404

    def test_log_message_is_noop(self):
        """Test that log_message is a no-op (suppresses default logging)."""
        mock_client = Mock()
        Handler = nw.create_handler(mock_client)
        handler = Handler.__new__(Handler)

        # Should return None and not raise
        result = handler.log_message("format", "arg1", "arg2")
        assert result is None


class TestStartHttpServer:
    """Tests for start_http_server function."""

    def test_start_http_server(self):
        """Test that HTTP server is started in a daemon thread."""
        mock_client = Mock()

        with (
            patch.object(nw, "ThreadingHTTPServer") as mock_server_cls,
            patch.object(nw.threading, "Thread") as mock_thread_cls,
        ):
            mock_server = Mock()
            mock_server_cls.return_value = mock_server
            mock_thread = Mock()
            mock_thread_cls.return_value = mock_thread

            nw.start_http_server(mock_client)

            mock_server_cls.assert_called_once()
            mock_thread_cls.assert_called_once()
            call_kwargs = mock_thread_cls.call_args[1]
            assert call_kwargs["daemon"] is True
            mock_thread.start.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
