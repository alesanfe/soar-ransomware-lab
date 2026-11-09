"""Structural validation for the soar-api Helm chart (no helm binary needed).

Validates chart metadata, values sanity, template/resource consistency and
security defaults. Full `helm template` rendering is validated in CI when a
runner has helm installed.
"""

import re
from pathlib import Path

import yaml

CHART = Path(__file__).resolve().parents[2] / "charts" / "soar-api"


class TestChartMetadata:
    def test_chart_yaml_valid(self):
        data = yaml.safe_load((CHART / "Chart.yaml").read_text())
        assert data["apiVersion"] == "v2"
        assert data["name"] == "soar-api"
        assert data["type"] == "application"
        assert "version" in data and "appVersion" in data

    def test_values_yaml_valid(self):
        data = yaml.safe_load((CHART / "values.yaml").read_text())
        assert data["service"]["port"] == 8000
        assert data["podSecurityContext"]["runAsNonRoot"] is True
        assert data["securityContext"]["allowPrivilegeEscalation"] is False
        assert data["securityContext"]["readOnlyRootFilesystem"] is True
        assert "ALL" in data["securityContext"]["capabilities"]["drop"]

    def test_no_secrets_in_values(self):
        """values.yaml must only reference secret names, never values."""
        text = (CHART / "values.yaml").read_text()
        for key in re.findall(r"^\s{4}- (\w+)$", text, re.MULTILINE):
            assert key.isupper(), f"non-secret-format key {key}"
        assert "password:" not in text.lower().replace("PASSWORD", "")


class TestTemplates:
    def test_required_templates_exist(self):
        templates = {p.name for p in (CHART / "templates").glob("*.yaml")}
        assert {"deployment.yaml", "service.yaml", "serviceaccount.yaml"} <= templates

    def test_template_braces_balanced(self):
        for tpl in (CHART / "templates").glob("*.yaml"):
            text = tpl.read_text()
            assert text.count("{{") == text.count("}}"), f"unbalanced braces in {tpl.name}"

    def test_deployment_references_secret_names_not_literals(self):
        dep = (CHART / "templates" / "deployment.yaml").read_text()
        assert "secretKeyRef" in dep
        assert "password:" not in dep.lower()

    def test_deployment_security_posture_rendered_from_values(self):
        dep = (CHART / "templates" / "deployment.yaml").read_text()
        assert "securityContext" in dep
        assert "livenessProbe" in dep and "readinessProbe" in dep

    def test_otel_and_bulkhead_env_wired(self):
        dep = (CHART / "templates" / "deployment.yaml").read_text()
        vals = (CHART / "values.yaml").read_text()
        # env keys flow from values.env through the range loop
        assert "range $k, $v := .Values.env" in dep
        for key in ("OTEL_ENABLED", "OTEL_EXPORTER_OTLP_ENDPOINT", "SOAR_BULKHEAD_CONCURRENT"):
            assert key in vals

    def test_service_account_no_automount(self):
        sa = yaml.safe_load((CHART / "values.yaml").read_text())
        assert sa["serviceAccount"]["automountToken"] is False
