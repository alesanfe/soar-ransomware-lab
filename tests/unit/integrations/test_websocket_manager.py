#!/usr/bin/env python3
"""Unit tests for websocket_manager.py."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from soar_lab.infrastructure.websocket_manager import ConnectionManager


class TestConnectionManager:
    """Test ConnectionManager."""

    def test_initialization(self):
        """Test successful initialization."""
        manager = ConnectionManager()

        assert manager.active_connections == []

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting a WebSocket."""
        manager = ConnectionManager()
        mock_websocket = Mock()
        mock_websocket.accept = AsyncMock()

        await manager.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()
        assert mock_websocket in manager.active_connections
        assert len(manager.active_connections) == 1

    @pytest.mark.asyncio
    async def test_connect_multiple(self):
        """Test connecting multiple WebSockets."""
        manager = ConnectionManager()
        mock_ws1 = Mock()
        mock_ws1.accept = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.accept = AsyncMock()

        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)

        assert len(manager.active_connections) == 2
        assert mock_ws1 in manager.active_connections
        assert mock_ws2 in manager.active_connections

    def test_disconnect(self):
        """Test disconnecting a WebSocket."""
        manager = ConnectionManager()
        mock_websocket = Mock()
        manager.active_connections.append(mock_websocket)

        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections
        assert len(manager.active_connections) == 0

    def test_disconnect_not_found(self):
        """Test disconnecting a WebSocket that is not in active connections."""
        manager = ConnectionManager()
        mock_websocket = Mock()

        manager.disconnect(mock_websocket)

        # Should not raise an error
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Test sending a personal message to a specific WebSocket."""
        manager = ConnectionManager()
        mock_websocket = Mock()
        mock_websocket.send_text = AsyncMock()

        await manager.send_personal_message("test message", mock_websocket)

        mock_websocket.send_text.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting a message to all active connections."""
        manager = ConnectionManager()
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()
        manager.active_connections = [mock_ws1, mock_ws2]

        message = {"type": "log", "content": "test"}
        await manager.broadcast(message)

        expected_message = json.dumps(message)
        mock_ws1.send_text.assert_called_once_with(expected_message)
        mock_ws2.send_text.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_broadcast_with_disconnect(self):
        """Test broadcasting when a connection disconnects."""
        manager = ConnectionManager()
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()
        manager.active_connections = [mock_ws1, mock_ws2]

        from fastapi import WebSocketDisconnect

        mock_ws1.send_text.side_effect = WebSocketDisconnect(code=1000)

        message = {"type": "log", "content": "test"}
        await manager.broadcast(message)

        # ws1 should be removed due to disconnect
        assert mock_ws1 not in manager.active_connections
        assert mock_ws2 in manager.active_connections
        assert len(manager.active_connections) == 1

    @pytest.mark.asyncio
    async def test_broadcast_with_generic_exception(self):
        """Test broadcasting when a connection raises a generic exception."""
        manager = ConnectionManager()
        mock_ws1 = Mock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock()
        mock_ws2.send_text = AsyncMock()
        manager.active_connections = [mock_ws1, mock_ws2]

        mock_ws1.send_text.side_effect = Exception("Connection error")

        message = {"type": "log", "content": "test"}
        await manager.broadcast(message)

        # ws1 should be removed due to exception
        assert mock_ws1 not in manager.active_connections
        assert mock_ws2 in manager.active_connections
        assert len(manager.active_connections) == 1

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self):
        """Test broadcasting with no active connections."""
        manager = ConnectionManager()

        message = {"type": "log", "content": "test"}
        await manager.broadcast(message)

        # Should not raise an error
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_connect_disconnect_cycle(self):
        """Test connect and disconnect cycle."""
        manager = ConnectionManager()
        mock_websocket = Mock()
        mock_websocket.accept = AsyncMock()

        await manager.connect(mock_websocket)
        assert len(manager.active_connections) == 1

        manager.disconnect(mock_websocket)
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_does_not_skip_connections_after_removal(self):
        """Bug: mutating active_connections inside the loop skips the
        connection that follows a failed one."""
        manager = ConnectionManager()
        ws1, ws2 = Mock(), Mock()
        ws1.send_text = AsyncMock(side_effect=Exception("gone"))
        ws2.send_text = AsyncMock()
        manager.active_connections = [ws1, ws2]

        await manager.broadcast({"type": "log"})

        ws2.send_text.assert_awaited_once()  # ws2 must still receive the message
        assert ws1 not in manager.active_connections
        assert ws2 in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnect_during_send(self):
        """Bug: if the connection is removed while send_text runs, the
        unguarded list.remove() in the except handler raises ValueError
        out of broadcast()."""
        manager = ConnectionManager()
        ws1, ws2 = Mock(), Mock()
        manager.active_connections = [ws1, ws2]

        async def _fail_and_detach(_msg):
            manager.active_connections.remove(ws1)
            raise Exception("gone")

        ws1.send_text = AsyncMock(side_effect=_fail_and_detach)
        ws2.send_text = AsyncMock()

        await manager.broadcast({"type": "log"})  # must not raise ValueError
        ws2.send_text.assert_awaited_once()
