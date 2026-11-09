"""Regression test: /ws/logs must unregister the connection even when
send_json raises a non-WebSocketDisconnect error (dead socket)."""

import pytest


class _FakeWS:
    def __init__(self, exc):
        self.exc = exc
        self.sent = 0

    async def send_json(self, data):
        self.sent += 1
        raise self.exc


class _FakeManager:
    def __init__(self):
        self.connected = []
        self.disconnected = []

    async def connect(self, ws):
        self.connected.append(ws)

    def disconnect(self, ws):
        self.disconnected.append(ws)


class _Cfg(dict):
    def get(self, k, d=None):
        return super().get(k, d)


@pytest.mark.asyncio
async def test_ws_logs_disconnects_on_send_runtime_error():
    """Bug: only WebSocketDisconnect triggered disconnect(); a RuntimeError
    from send_json (dead socket) left a ghost connection in the manager."""
    from soar_lab.interfaces.api.main import create_app

    mgr = _FakeManager()
    # API_REQUIRE_AUTH=false: this test exercises the send/disconnect
    # cleanup path, not the ticket gate (WEB-AUTH is covered by
    # test_ws_ticket.py). With auth on, a ticket-less fake socket is
    # closed at 4401 before send_json ever runs.
    app = create_app(
        config_provider=_Cfg(ACTIVE=True, API_REQUIRE_AUTH="false"),
        websocket_manager=mgr,
        auth_service=object(),
    )
    app.state.log_reader = None

    route = next(r for r in app.routes if getattr(r, "path", "") == "/ws/logs")
    ws = _FakeWS(RuntimeError("socket dead"))

    with pytest.raises(RuntimeError):
        await route.endpoint(websocket=ws, connection_manager=mgr)

    assert mgr.disconnected == [ws], "ghost connection leaked in manager"
