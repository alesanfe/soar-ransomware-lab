"""Unit tests for api.composition module."""

from unittest.mock import Mock, patch

import pytest

from soar_lab.interfaces.api.composition import CompositionRoot, create_app


class TestCompositionRoot:
    """Tests for CompositionRoot class."""

    def test_composition_root_init_missing_base_dir(self):
        """Test CompositionRoot raises ValueError when base_dir is not
        provided."""
        with patch("soar_lab.interfaces.api.composition.create_settings") as mock_settings:
            mock_settings.return_value = {}
            with patch(
                "soar_lab.interfaces.api.composition.InfrastructureConfigProvider"
            ) as mock_config_provider:
                mock_config = Mock()
                mock_config.get.return_value = None  # base_dir is None
                mock_config_provider.return_value = mock_config

                with pytest.raises(ValueError):
                    CompositionRoot()


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_create_app_returns_fastapi(self):
        """Test create_app returns FastAPI instance."""
        with patch("soar_lab.interfaces.api.composition.CompositionRoot") as mock_composition_root:
            mock_composition = Mock()
            mock_app = Mock()
            mock_composition.create_fastapi_app.return_value = mock_app
            mock_composition_root.return_value = mock_composition

            app = create_app()

            assert app == mock_app
            mock_composition_root.assert_called_once()
            mock_composition.create_fastapi_app.assert_called_once()


def _mock_root_deps(monkeypatch, cfg_map=None):
    """Patch every collaborator CompositionRoot wires, with a fake config."""
    from unittest.mock import MagicMock

    import soar_lab.interfaces.api.composition as comp

    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: (cfg_map or {}).get(k, d)
    settings = MagicMock()
    settings.validate.return_value = True
    monkeypatch.setattr(comp, "create_settings", lambda: settings)
    monkeypatch.setattr(comp, "InfrastructureConfigProvider", lambda s: cfg)
    for name in (
        "PathService", "FilesystemStorage", "ElasticsearchAlertRepository",
        "SystemMetricsDriver", "AioHTTPClient", "HTTPHealthCheckAdapter",
        "ExecutionLogParser", "CSVKPIFormatter", "FileLogReader",
        "PytestOutputParser", "PytestTestRunner", "TarBackupDriver",
        "SubprocessRunner", "ConnectionManager", "StatisticalCalculator",
        "KPIAnalyzer", "JWTTokenProvider", "AuthService", "AnalyticsService",
        "BackupService", "TestService", "HealthService",
    ):
        monkeypatch.setattr(comp, name, MagicMock())
    monkeypatch.setattr(comp, "create_docker_client", MagicMock())
    monkeypatch.setattr(comp, "create_redis_client", MagicMock())
    monkeypatch.setattr(comp, "build_integration_clients", MagicMock(return_value={}))
    monkeypatch.setattr(comp, "setup_logging", MagicMock())
    monkeypatch.setattr(comp, "verify_tls", MagicMock())
    monkeypatch.setattr(comp, "set_default_factories", MagicMock())
    return comp, cfg


class TestCompositionRootWiring:
    """Wiring paths inside CompositionRoot.__init__ (API-EVAL-003 guards)."""

    def test_workers_gt1_with_memory_backend_fails_closed(self, monkeypatch):
        import pytest

        _mock_root_deps(monkeypatch, {"UVICORN_WORKERS": "4", "base_dir": "/tmp"})
        with pytest.raises(RuntimeError, match="RATE_LIMIT_BACKEND"):
            CompositionRoot()

    def test_workers_gt1_with_redis_backends_boots(self, monkeypatch):
        _mock_root_deps(
            monkeypatch,
            {
                "UVICORN_WORKERS": "4",
                "RATE_LIMIT_BACKEND": "redis",
                "WS_TICKET_BACKEND": "redis",
                "base_dir": "/tmp",
            },
        )
        root = CompositionRoot()
        assert root is not None

    def test_invalid_workers_value_treated_as_one(self, monkeypatch):
        _mock_root_deps(monkeypatch, {"UVICORN_WORKERS": "notanint", "base_dir": "/tmp"})
        assert CompositionRoot() is not None

    def test_full_wiring_registers_default_factories_and_services(self, monkeypatch):
        comp, _ = _mock_root_deps(
            monkeypatch, {"base_dir": "/tmp", "log_dir": "/tmp/logs"}
        )
        root = CompositionRoot()
        comp.set_default_factories.assert_called_once()
        comp.PathService.assert_called_once()
        assert root.path_service.ensure_directories.called

    def test_warn_unconfigured_integrations_logs(self, monkeypatch, caplog):
        import logging

        comp, _ = _mock_root_deps(monkeypatch, {"base_dir": "/tmp"})
        with caplog.at_level(logging.WARNING):
            root = CompositionRoot()
            root._warn_unconfigured_integrations()
        assert "without config" in caplog.text

    def test_create_fastapi_app_delegates(self, monkeypatch):
        from unittest.mock import MagicMock

        comp, _ = _mock_root_deps(monkeypatch, {"base_dir": "/tmp"})
        injected = MagicMock()
        monkeypatch.setattr(comp, "create_injected_app", injected)
        root = CompositionRoot()
        root.create_fastapi_app()
        assert injected.called
        assert injected.call_args.kwargs["admission_service"] is None
