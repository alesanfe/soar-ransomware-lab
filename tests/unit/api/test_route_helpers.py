#!/usr/bin/env python3
"""Unit tests for route_helpers dependency factories.

Documents the actual contract: ``make_state_getter`` guards *None* values
with 503 (service wired but unconfigured), while a *missing* attribute
propagates AttributeError — the 503 path only holds because composition
always defines the attribute.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from soar_lab.interfaces.api.route_helpers import (
    make_simple_getter,
    make_state_getter,
)


def _app(**state):
    app = Mock()
    app.state = SimpleNamespace(**state)
    return app


class TestMakeStateGetter:
    def test_returns_value_when_set(self):
        app = _app(svc={"name": "x"})
        getter = make_state_getter(app, "svc", "Service")
        assert getter() == {"name": "x"}

    def test_raises_503_when_value_is_none(self):
        app = _app(svc=None)
        getter = make_state_getter(app, "svc", "Service")
        with pytest.raises(HTTPException) as ei:
            getter()
        assert ei.value.status_code == 503
        assert "Service not available" in ei.value.detail

    def test_missing_attribute_raises_attribute_error(self):
        """Contract: the 503 guard only covers None — a state attr that was
        never set propagates AttributeError (composition always defines
        wired attrs, so this signals a wiring bug, not unavailability)."""
        app = _app()
        getter = make_state_getter(app, "never_set", "Service")
        with pytest.raises(AttributeError):
            getter()


class TestMakeSimpleGetter:
    def test_returns_value_without_none_check(self):
        app = _app(thing=None)
        getter = make_simple_getter(app, "thing")
        assert getter() is None

    def test_returns_value(self):
        app = _app(thing=42)
        getter = make_simple_getter(app, "thing")
        assert getter() == 42


class TestGetterFactories:
    """The returned closures hit getattr/503 branches."""

    def _app(self, **state):
        from fastapi import FastAPI

        app = FastAPI()
        for k, v in state.items():
            setattr(app.state, k, v)
        return app

    def test_state_getter_returns_value(self):
        from soar_lab.interfaces.api.route_helpers import make_state_getter

        get = make_state_getter(self._app(svc="S"), "svc", "Service")
        assert get() == "S"

    def test_state_getter_none_raises_503(self):
        import pytest
        from fastapi import HTTPException

        from soar_lab.interfaces.api.route_helpers import make_state_getter

        get = make_state_getter(self._app(svc=None), "svc", "Service")
        with pytest.raises(HTTPException) as exc:
            get()
        assert exc.value.status_code == 503
        assert "Service not available" in exc.value.detail

    def test_simple_getter_returns_attr(self):
        from soar_lab.interfaces.api.route_helpers import make_simple_getter

        sentinel = object()
        get = make_simple_getter(self._app(thing=sentinel), "thing")
        assert get() is sentinel
