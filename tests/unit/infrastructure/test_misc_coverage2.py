#!/usr/bin/env python3
"""Coverage: validate_credentials._sync_conf/_validate_file_defaults,
secret_generator methods, shuffle_es_helpers ES lookups."""

from unittest.mock import Mock, patch

# ---------- validate_credentials ----------


class TestSyncConf:
    def test_missing_file_returns_empty(self, tmp_path):
        from soar_lab.infrastructure import validate_credentials as vc

        assert vc._sync_config_file(tmp_path / "nope.conf", {}) == []

    def test_replaces_mapped_values_and_writes(self, tmp_path):
        from soar_lab.infrastructure import validate_credentials as vc

        conf = tmp_path / "thehive.conf"
        conf.write_text('secret = "old-secret"\n', encoding="utf-8")
        fake_map = {conf.name: [("THEHIVE_SECRET", r'secret = "([^"]+)"')]}
        with patch.object(vc, "_CONF_MAP", fake_map):
            changes = vc._sync_config_file(conf, {"THEHIVE_SECRET": "new-secret"})
        assert changes == ["thehive.conf: updated THEHIVE_SECRET value"]
        assert 'secret = "new-secret"' in conf.read_text(encoding="utf-8")

    def test_skips_missing_env_and_no_change_no_write(self, tmp_path):
        from soar_lab.infrastructure import validate_credentials as vc

        conf = tmp_path / "thehive.conf"
        conf.write_text('secret = "same"\n', encoding="utf-8")
        fake_map = {conf.name: [("THEHIVE_SECRET", r'secret = "([^"]+)"')]}
        with patch.object(vc, "_CONF_MAP", fake_map):
            assert vc._sync_config_file(conf, {"OTHER": "x"}) == []  # env not present
            assert vc._sync_config_file(conf, {"THEHIVE_SECRET": "same"}) == []


class TestValidateFileDefaults:
    def test_missing_file_warns_and_override_infos(self, tmp_path):
        from soar_lab.infrastructure import validate_credentials as vc

        present = tmp_path / "f.py"
        present.write_text("x", encoding="utf-8")
        missing = tmp_path / "gone.py"

        def extract(p):
            return {"K": "default"}

        info, warnings = vc._validate_file_defaults(
            [present, missing], {"K": "override"}, ["K"], extract
        )
        assert any("K" in i for i in info)
        assert any("gone.py" in w for w in warnings)


# ---------- security/secret_generator.py ----------


class TestSecretGeneratorMethods:
    def test_api_key_long_and_composition(self):
        from soar_lab.security.secret_generator import SecretGeneratorService

        key = SecretGeneratorService().generate_api_key(40)
        assert len(key) == 40

    def test_webhook_jwt_secret_key_token(self):
        from soar_lab.security.secret_generator import SecretGeneratorService as S

        s = S()
        assert len(s.generate_webhook_token(32)) == 32
        assert len(s.generate_jwt_secret(32)) == 32
        assert len(s.generate_secret_key(16)) == 16
        assert len(s.generate_token(24)) <= 24 and len(s.generate_token(24)) > 0

    def test_validate_secret_format(self):
        from soar_lab.security.secret_generator import validate_secret_format

        assert validate_secret_format("abc", 3, "abc") is True
        assert validate_secret_format("abc", 2, "abc") is False
        assert validate_secret_format("", 3, "abc") is False
        assert validate_secret_format("abd", 3, "abc") is False

    def test_generate_all_secrets_with_and_without_fs(self, tmp_path):
        from soar_lab.security.secret_generator import SecretGeneratorService

        out = tmp_path / "s.json"
        fs = Mock()
        s = SecretGeneratorService(file_system=fs)
        data = s.generate_all_secrets(str(out))
        fs.write_file.assert_called_once()
        assert data["generated_at"].endswith("Z")
        # module-level bindings exercise the default service
        import soar_lab.security.secret_generator as sg

        assert sg.generate_password() and sg.generate_token(8)


# ---------- shuffle_es_helpers ----------


class TestShuffleEsHelpers:
    def test_fetch_first_user_source_hit(self):
        from soar_lab.infrastructure.integrations.shuffle import shuffle_es_helpers as h

        resp = Mock(status_code=200)
        resp.json.return_value = {"hits": {"hits": [{"_source": {"username": "u1"}}]}}
        with (
            patch.object(h, "get_es_connection", return_value=("http://es", None, False)),
            patch.object(h, "_es_session") as sess,
        ):
            sess.return_value.get.return_value = resp
            assert h.fetch_first_user_source() == {"username": "u1"}

    def test_fetch_first_user_source_empty_and_error(self):
        from soar_lab.infrastructure.integrations.shuffle import shuffle_es_helpers as h

        resp = Mock(status_code=200)
        resp.json.return_value = {"hits": {"hits": []}}
        with (
            patch.object(h, "get_es_connection", return_value=("http://es", None, False)),
            patch.object(h, "_es_session") as sess,
        ):
            sess.return_value.get.return_value = resp
            assert h.fetch_first_user_source() is None
            sess.return_value.get.side_effect = RuntimeError("down")
            assert h.fetch_first_user_source() is None

    def test_es_workflow_executions_with_ids_returns_list(self):
        from soar_lab.infrastructure.integrations.shuffle import shuffle_es_helpers as h

        hits = [{"_source": {"execution_id": "e1"}}, {"_source": {"execution_id": "e2"}}]
        with patch.object(h, "_es_search", return_value=hits) as search:
            out = h.es_workflow_executions("wf1", ["e1", "e2"])
        assert [e["execution_id"] for e in out] == ["e1", "e2"]
        q = search.call_args.args[0]
        assert "results" in q["_source"]
        assert q["size"] == 2

    def test_es_workflow_executions_none_when_no_hits(self):
        from soar_lab.infrastructure.integrations.shuffle import shuffle_es_helpers as h

        with patch.object(h, "_es_search", return_value=None):
            assert h.es_workflow_executions("wf1") is None
