#!/usr/bin/env python3
"""WEB-AUTH-001/002/003/004 + WEB-TEST-007 — WebSocket ticket security.

Covers:
- store: single-use, expiry, pending-per-user limit
- scope: logs:read enforcement (WEB-AUTH-003)
- endpoint: 4401 missing/invalid/reused, 4408 expired, 4403 no-scope,
  4429 per-user connection limit, valid-ticket happy path, ticket never
  appears in logs (WEB-AUTH-005).
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from soar_lab.infrastructure.websocket_manager import ConnectionManager
from soar_lab.infrastructure.ws_ticket_store import (
    RedisWsTicketStore,
    TicketIssueError,
    WsTicketStore,
    has_logs_read_scope,
)
from soar_lab.interfaces.api.main import create_app


class TestWsTicketStore:
    def test_issue_and_consume(self):
        s = WsTicketStore()
        t = s.issue("alice")
        r = s.consume(t)
        assert r.ok and r.user == "alice"

    def test_single_use_reuse_fails(self):
        s = WsTicketStore()
        t = s.issue("alice")
        assert s.consume(t).ok
        r = s.consume(t)
        assert not r.ok  # deleted after first consume → indistinguishable

    def test_expired_ticket_fails(self):
        s = WsTicketStore(ttl=-1)  # already expired on issue
        t = s.issue("alice")
        r = s.consume(t)
        assert not r.ok and r.reason == "expired"

    def test_unknown_and_empty_rejected(self):
        s = WsTicketStore()
        assert not s.consume("nope").ok
        assert not s.consume(None).ok
        assert not s.consume("").ok

    def test_pending_per_user_limit(self):
        s = WsTicketStore(max_pending_per_user=2)
        s.issue("alice")
        s.issue("alice")
        with pytest.raises(TicketIssueError):
            s.issue("alice")
        s.issue("bob")  # other users unaffected

    def test_user_binding(self):
        s = WsTicketStore()
        t = s.issue("alice")
        assert s.consume(t).user == "alice"


class _FakeRedis:
    """Minimal in-memory stand-in for the Redis commands the store uses."""

    def __init__(self):
        self._data = {}

    def incr(self, key):
        self._data[key] = int(self._data.get(key) or 0) + 1
        return self._data[key]

    def decr(self, key):
        self._data[key] = int(self._data.get(key) or 0) - 1
        return self._data[key]

    def expire(self, key, _ttl):
        return True

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self._data:
            return None
        self._data[key] = value
        return True

    def getdel(self, key):
        return self._data.pop(key, None)

    def scan_iter(self, match="*"):
        prefix = match.rstrip("*")
        return [k for k in list(self._data) if k.startswith(prefix)]


class TestRedisWsTicketStore:
    """Multi-worker ticket store — same contract, atomic GETDEL consume."""

    def _store(self):
        return RedisWsTicketStore(_FakeRedis())

    def test_issue_and_consume(self):
        s = self._store()
        t = s.issue("alice")
        r = s.consume(t)
        assert r.ok and r.user == "alice"

    def test_single_use_reuse_fails(self):
        s = self._store()
        t = s.issue("alice")
        assert s.consume(t).ok
        assert not s.consume(t).ok

    def test_pending_limit_enforced(self):
        s = self._store()
        for _ in range(s.max_pending_per_user):
            s.issue("alice")
        with pytest.raises(TicketIssueError):
            s.issue("alice")
        s.issue("bob")

    def test_missing_and_empty_tokens_invalid(self):
        s = self._store()
        assert not s.consume(None).ok
        assert not s.consume("nonexistent").ok

    def test_consume_denies_when_redis_down(self):
        s = self._store()

        class _Down(_FakeRedis):
            def getdel(self, key):
                raise ConnectionError("redis unreachable")

        s._r = _Down()
        assert not s.consume("anything").ok

    def test_user_binding(self):
        s = self._store()
        t = s.issue("alice")
        assert s.consume(t).user == "alice"


class TestScope:
    def test_no_scopes_claim_lab_v1_grants(self):
        assert has_logs_read_scope({"user": "admin"})

    def test_scopes_present_enforced(self):
        assert not has_logs_read_scope({"user": "u", "scopes": ["backup:run"]})
        assert has_logs_read_scope({"user": "u", "scopes": ["logs:read"]})


def _cp(auth_required="true"):
    cp = Mock()
    cp.get.side_effect = lambda key, default=None: {
        "API_REQUIRE_AUTH": auth_required,
        "API_DOCS_ENABLED": "false",
        "DOCS_DIR": "/nonexistent",
        "CORS_ORIGINS": ["*"],
    }.get(key, default)
    cp.get_service_urls.return_value = {}
    return cp


def _auth(user_info=None):
    a = Mock()
    a.verify_jwt_token.return_value = user_info or {"user": "admin"}
    return a


def _app(auth_required="true", user_info=None, websocket_manager=None):
    return create_app(
        config_provider=_cp(auth_required),
        auth_service=_auth(user_info),
        websocket_manager=websocket_manager or ConnectionManager(),
        log_reader=None,
        system_metrics=Mock(),
        health_service=Mock(),
        analytics_service=Mock(),
        backup_service=Mock(),
        test_service=Mock(),
        storage=Mock(),
        path_service=Mock(),
    )


HDRS = {"Authorization": "Bearer test-jwt"}


def _ticket(client):
    r = client.post("/auth/ws-ticket", headers=HDRS)
    assert r.status_code == 200, r.text
    return r.json()["ticket"]


class TestWsTicketEndpoint:
    def test_ticket_endpoint_requires_auth(self):
        client = TestClient(_app())
        assert client.post("/auth/ws-ticket").status_code == 401

    def test_ticket_endpoint_no_scope_403(self):
        client = TestClient(_app(user_info={"user": "u", "scopes": ["backup:run"]}))
        assert client.post("/auth/ws-ticket", headers=HDRS).status_code == 403

    def test_ticket_response_shape(self):
        client = TestClient(_app())
        r = client.post("/auth/ws-ticket", headers=HDRS)
        data = r.json()
        assert data["ticket"] and data["expires_in"] == 30
        assert len(data["ticket"]) >= 32

    def test_pending_ticket_rate_limit_429(self):
        app = _app()
        client = TestClient(app)
        for _ in range(5):
            assert client.post("/auth/ws-ticket", headers=HDRS).status_code == 200
        r = client.post("/auth/ws-ticket", headers=HDRS)
        assert r.status_code == 429
        assert "Retry-After" in r.headers


class TestWsLogsGate:
    def _close_code(self, client, path):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(path):
                pass
        return exc.value.code

    def test_no_ticket_4401(self):
        client = TestClient(_app())
        assert self._close_code(client, "/ws/logs") == 4401

    def test_invalid_ticket_4401(self):
        client = TestClient(_app())
        assert self._close_code(client, "/ws/logs?ticket=forged") == 4401

    def test_expired_ticket_4408(self):
        app = _app()
        client = TestClient(app)
        # Swap in an already-expired store and mint a dead ticket.
        app.state.ws_ticket_store = WsTicketStore(ttl=-1)
        t = app.state.ws_ticket_store.issue("admin")
        assert self._close_code(client, f"/ws/logs?ticket={t}") == 4408

    def test_valid_ticket_connects_then_reuse_fails(self):
        client = TestClient(_app())
        t = _ticket(client)
        with client.websocket_connect(f"/ws/logs?ticket={t}") as ws:
            entry = ws.receive_json()
            assert "timestamp" in entry
        # Second use of the same ticket → 4401
        assert self._close_code(client, f"/ws/logs?ticket={t}") == 4401

    def test_per_user_connection_limit_4429(self):
        client = TestClient(_app())
        conns = []
        for _ in range(3):
            t = _ticket(client)
            ws = client.websocket_connect(f"/ws/logs?ticket={t}")
            conns.append(ws)
            ws.__enter__()
        try:
            t4 = _ticket(client)
            assert self._close_code(client, f"/ws/logs?ticket={t4}") == 4429
        finally:
            for ws in conns:
                ws.__exit__(None, None, None)

    def test_counts_released_after_disconnect(self):
        client = TestClient(_app())
        connected = 0
        for _ in range(4):
            t = _ticket(client)
            with client.websocket_connect(f"/ws/logs?ticket={t}") as ws:
                ws.receive_json()
            connected += 1
        # 4 sequential connects succeeded → counts decremented on close
        assert connected == 4

    def test_ticket_never_logged(self, caplog):
        client = TestClient(_app())
        t = _ticket(client)
        with client.websocket_connect(f"/ws/logs?ticket={t}") as ws:
            ws.receive_json()
        assert t not in caplog.text

    def test_service_token_can_issue_ticket(self):
        app = _app()
        cp = app.state.config_provider
        cp.get.side_effect = lambda key, default=None: {
            "API_REQUIRE_AUTH": "true",
            "API_DOCS_ENABLED": "false",
            "DOCS_DIR": "/nonexistent",
            "CORS_ORIGINS": ["*"],
            "INTERNAL_SERVICE_TOKEN": "svc-secret",
        }.get(key, default)
        client = TestClient(app)
        r = client.post("/auth/ws-ticket", headers={"X-Service-Token": "svc-secret"})
        assert r.status_code == 200

    def test_auth_off_lab_mode_still_connects(self):
        client = TestClient(_app(auth_required="false"))
        with client.websocket_connect("/ws/logs") as ws:
            assert "timestamp" in ws.receive_json()


class TestScopeStringClaims:
    """BUG: ``has_logs_read_scope`` substring-matches string claims.

    ``"admin" in roles`` and ``LOGS_READ_SCOPE in scopes`` use ``in`` on
    *strings* — Python falls back to substring matching, so claims that are
    strings (JWT ``scope`` is a space-delimited string per RFC 6749, and
    IdPs often emit ``roles`` as a single string) grant on any scope/role
    that merely CONTAINS the required value.
    """

    def test_role_administrator_should_not_grant(self):
        # "administrator" is not an admin/operator role — but it contains
        # the substring "admin", so the check grants it anyway.
        assert not has_logs_read_scope({"user": "u", "roles": "administrator"})

    def test_scope_logs_reader_should_not_grant(self):
        # "logs:reader" is a different scope — but it contains the
        # substring "logs:read", so the check grants it anyway.
        assert not has_logs_read_scope({"user": "u", "scopes": "logs:reader"})

    def test_scope_string_exact_grant_still_works(self):
        # Correct behaviour we must keep: an exact scope string grants.
        assert has_logs_read_scope({"user": "u", "scopes": "logs:read"})
        # …and a space-delimited list containing the exact scope grants.
        assert has_logs_read_scope({"user": "u", "scopes": "other logs:read"})


class TestMemoryConsumeRace:
    """``WsTicketStore.consume`` must stay race-safe (BUG-WST-02).

    The store removes tickets atomically via ``pop``: two threads racing
    on the same token can never both fetch it — the loser observes
    ``None`` and is reported ``invalid``. The pre-fix ``get``+``del``
    sequence let the losing thread's ``del`` raise a bare ``KeyError``
    (a 500) instead of a clean ``ConsumeResult``. Here the losing side is
    simulated deterministically — ``pop`` returns ``default`` because the
    winner already removed the entry.
    """

    def test_lost_race_returns_clean_result_not_exception(self):
        class _LostRace(dict):
            def pop(self, key, default=None):
                return default  # the winner already removed it

        s = WsTicketStore()
        token = s.issue("alice")
        s._tickets = _LostRace(s._tickets)
        result = s.consume(token)
        assert not result.ok
        assert result.reason in ("invalid", "consumed")


class TestRedisPendingAccounting:
    """BUGS in RedisWsTicketStore pending-counter bookkeeping."""

    def _store(self):
        return RedisWsTicketStore(_FakeRedis())

    def test_consume_on_expired_pending_counter_goes_negative(self):
        # Pending counters carry a TTL (ttl+60). When it lapses before the
        # ticket is consumed, ``decr`` recreates the key at -1 with NO TTL —
        # permanently gifting the user one extra pending slot.
        s = self._store()
        token = s.issue("alice")
        s._r._data.pop(f"{s.PENDING_PREFIX}alice")  # counter TTL lapsed
        assert s.consume(token).ok
        assert s._r._data[f"{s.PENDING_PREFIX}alice"] == 0  # BUG: it is -1

    def test_issue_leaks_pending_when_set_fails(self):
        # ``incr`` runs before ``set``; when the ticket write fails the
        # increment must be rolled back, else redis blips inflate the
        # user's pending count and lock them out with zero live tickets.
        class _Recovers(_FakeRedis):
            def __init__(self):
                super().__init__()
                self.fails = 2

            def set(self, key, value, ex=None, nx=False):
                if self.fails:
                    self.fails -= 1
                    raise ConnectionError("redis blip")
                return super().set(key, value, ex=ex, nx=nx)

        s = RedisWsTicketStore(_Recovers(), max_pending_per_user=2)
        for _ in range(2):
            with pytest.raises(ConnectionError):
                s.issue("alice")
        # Backend healthy again — the two failed attempts must not count.
        s.issue("alice")  # pre-fix: TicketIssueError despite zero live tickets


class TestConnectFailureCountLeak:
    """BUG: per-user WS connection count leaks when ``connect()`` raises.

    ``counts[user] += 1`` runs BEFORE ``connection_manager.connect()``,
    but the ``finally`` that decrements wraps only the streaming block —
    so a failed connect permanently consumes one of the user's 3 slots.
    After 3 failures the user is locked out with code 4429 while holding
    zero live connections.
    """

    def test_failed_connects_do_not_consume_slots(self):
        mgr = Mock()
        mgr.connect = AsyncMock(side_effect=RuntimeError("accept failed"))
        mgr.disconnect = Mock()
        app = _app(websocket_manager=mgr)
        client = TestClient(app)
        for _ in range(3):
            ticket = _ticket(client)
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/logs?ticket={ticket}"):
                    pass
        # Zero live connections — the count must be back to zero.
        counts = getattr(app.state, "ws_user_counts", {})
        assert counts.get("admin", 0) == 0, f"leaked slots: {counts}"
