"""Unit tests for config.webhook resolve_webhook_url."""

from __future__ import annotations

import json
from unittest.mock import patch

from soar_lab.common.runtime import is_inside_container
from soar_lab.config.webhook import resolve_webhook_url

# Env vars that can interfere with tests — cleared via _clean_env
_ENV_VARS = ("SHUFFLE_WEBHOOK_URL", "SIEM_WEBHOOK_TOKEN")


def _clean_env():
    """Return a context manager that clears webhook-related env vars."""
    return patch.dict("os.environ", {k: "" for k in _ENV_VARS}, clear=False)


class TestInsideContainer:
    """Tests for is_inside_container."""

    def test_returns_bool(self):
        result = is_inside_container()
        assert isinstance(result, bool)

    @patch("soar_lab.common.runtime.Path")
    def test_inside_container_true(self, mock_path):
        mock_path.return_value.exists.return_value = True
        mock_path.side_effect = lambda p: mock_path.return_value
        result = is_inside_container()
        assert result is True


class TestResolveWebhookUrl:
    """Tests for resolve_webhook_url."""

    def test_env_url_takes_priority(self):
        with _clean_env():
            result = resolve_webhook_url(env_url="http://example.com/webhook")
            assert result == "http://example.com/webhook"

    @patch.dict("os.environ", {"SHUFFLE_WEBHOOK_URL": "http://env.example.com/hook"})
    def test_env_variable_shuffle_webhook_url(self):
        result = resolve_webhook_url()
        assert result == "http://env.example.com/hook"

    def test_token_builds_backend_url(self):
        with _clean_env():
            result = resolve_webhook_url(token="abc123")
            assert result == "http://shuffle-backend:5001/api/v1/hooks/abc123"

    @patch.dict("os.environ", {"SIEM_WEBHOOK_TOKEN": "tok456"})
    def test_env_variable_siem_webhook_token(self):
        result = resolve_webhook_url()
        assert result == "http://shuffle-backend:5001/api/v1/hooks/tok456"

    def test_env_url_overrides_token(self):
        with _clean_env():
            result = resolve_webhook_url(env_url="http://url.com", token="tok")
            assert result == "http://url.com"

    def test_reads_from_webhook_info_json(self, tmp_path):
        info_file = tmp_path / "reports" / "validation" / "results" / "webhook_info.json"
        info_file.parent.mkdir(parents=True)
        info_file.write_text(
            json.dumps(
                {
                    "webhook_url": "http://internal:5001/hook",
                    "webhook_url_host": "http://localhost:5001/hook",
                }
            ),
            encoding="utf-8",
        )
        with _clean_env(), patch("soar_lab.config.webhook.is_inside_container", return_value=False):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result == "http://localhost:5001/hook"

    def test_reads_from_webhook_info_json_inside_container(self, tmp_path):
        info_file = tmp_path / "reports" / "validation" / "results" / "webhook_info.json"
        info_file.parent.mkdir(parents=True)
        info_file.write_text(
            json.dumps(
                {
                    "webhook_url": "http://internal:5001/hook",
                    "webhook_url_host": "http://localhost:5001/hook",
                }
            ),
            encoding="utf-8",
        )
        with _clean_env(), patch("soar_lab.config.webhook.is_inside_container", return_value=True):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result == "http://internal:5001/hook"

    def test_webhook_info_json_missing_url_fields(self, tmp_path):
        info_file = tmp_path / "reports" / "validation" / "results" / "webhook_info.json"
        info_file.parent.mkdir(parents=True)
        info_file.write_text(json.dumps({"other": "data"}), encoding="utf-8")
        with (
            _clean_env(),
            patch("soar_lab.config.webhook.is_inside_container", return_value=False),
            patch("soar_lab.config.webhook.WEBHOOK_INFO_PATHS", ()),
        ):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result is None

    def test_webhook_info_json_invalid_json(self, tmp_path):
        info_file = tmp_path / "reports" / "validation" / "results" / "webhook_info.json"
        info_file.parent.mkdir(parents=True)
        info_file.write_text("not valid json{", encoding="utf-8")
        with (
            _clean_env(),
            patch("soar_lab.config.webhook.is_inside_container", return_value=False),
            patch("soar_lab.config.webhook.WEBHOOK_INFO_PATHS", ()),
        ):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result is None

    def test_no_webhook_info_file_returns_none(self, tmp_path):
        with (
            _clean_env(),
            patch("soar_lab.config.webhook.is_inside_container", return_value=False),
            patch("soar_lab.config.webhook.WEBHOOK_INFO_PATHS", ()),
        ):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result is None

    def test_fallback_to_webhook_info_in_root(self, tmp_path):
        info_file = tmp_path / "webhook_info.json"
        info_file.write_text(
            json.dumps({"webhook_url_host": "http://fallback:5001/hook"}),
            encoding="utf-8",
        )
        with _clean_env(), patch("soar_lab.config.webhook.is_inside_container", return_value=False):
            result = resolve_webhook_url(base_dir=tmp_path)
        assert result == "http://fallback:5001/hook"

    def test_no_base_dir_no_env_returns_none(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("soar_lab.config.webhook.is_inside_container", return_value=False),
            patch("soar_lab.config.webhook.Path") as mock_path,
        ):
            # Make /app/reports/... not exist
            mock_path.return_value.exists.return_value = False
            mock_path.side_effect = lambda p: mock_path.return_value
            result = resolve_webhook_url()
            assert result is None
