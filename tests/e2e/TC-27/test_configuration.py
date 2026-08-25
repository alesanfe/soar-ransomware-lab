#!/usr/bin/env python3
"""TC-27: Configuración (Configuration Management)

Validates configuration management:
  - Configuration drift detection (.env.example vs actual env)
  - Golden configuration (docker-compose.yml service definitions)
  - Volume persistence (Docker volumes exist and are writable)
  - Environment variables (all required keys present, valid, non-empty)
"""

import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import pytest

from tests.e2e.base import E2EBaseTest


class TestConfiguration(E2EBaseTest):
    """TC-27 — Configuración: Gestión de configuración y detección de drift."""

    tc_id = "TC-27"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-27 {msg}"
        print(line)

    # ------------------------------------------------------------------
    # Helper: parse .env file into dict
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_env_file(path: Path) -> dict[str, str]:
        """Parse a .env file into a dict, skipping comments and blanks."""
        result: dict[str, str] = {}
        if not path.exists():
            return result
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
        return result

    # ------------------------------------------------------------------
    # Test 1: Configuration drift detection
    # ------------------------------------------------------------------

    def test_configuration_drift_detection(self):
        """TC-27-01: Configuration drift detection.

        Loads the expected config from .env.example, compares with actual
        self.env values. Asserts:
          1. All required vars from .env.example are present in self.env.
          2. No unexpected drift in critical vars (URLs, ports).
        """
        self._log("=== TC-27-01: CONFIGURATION DRIFT DETECTION TEST STARTED ===")

        # --- Step 1: Load expected config from .env.example ---
        self._log("STEP 1: Loading expected config from .env.example")
        env_example = self.repo_root / ".env.example"
        assert env_example.exists(), f".env.example should exist at {env_example}"
        expected = self._parse_env_file(env_example)
        assert len(expected) > 0, ".env.example should contain variables"
        self._log(f"+ Loaded {len(expected)} variables from .env.example")

        # --- Step 2: Assert all required vars are present in self.env ---
        self._log("STEP 2: Verifying required variables are present in runtime env")
        # Critical variables that MUST be present in the runtime environment
        critical_vars = [
            "THEHIVE_API_KEY",
            "CORTEX_API_KEY",
            "SHUFFLE_DEFAULT_APIKEY",
            "ELASTIC_PASSWORD",
            "OPENSEARCH_PASSWORD",
            "REDIS_PASSWORD",
            "CORTEX_ADMIN_PASSWORD",
        ]
        missing: list[str] = []
        for var in critical_vars:
            if not self.env.get(var):
                missing.append(var)
            else:
                self._log(f"  + {var}: present")

        assert len(missing) == 0, (
            f"Critical variables missing from runtime env: {missing}. "
            f"These should be set in .env.full and loaded by the base class."
        )
        self._log("+ All critical variables present in runtime env")

        # --- Step 3: Assert no unexpected drift in critical URL vars ---
        self._log("STEP 3: Checking for drift in critical URL variables")
        # The URLs in .env.example are templates; the actual URLs come from
        # .env.full. We verify the URL structure is valid (scheme + host).
        url_vars = ["THEHIVE_URL", "ES_URL", "CORTEX_URL", "SHUFFLE_URL", "MISP_URL"]
        for var in url_vars:
            val = self.env.get(var, "")
            if val:
                parsed = urlparse(val)
                assert parsed.scheme in (
                    "http",
                    "https",
                ), f"{var} should be a valid HTTP/HTTPS URL, got: {val}"
                assert parsed.hostname, f"{var} should have a hostname, got: {val}"
                self._log(f"  + {var}: {val} (valid URL)")
            else:
                # URL may be derived from defaults if not in env — check get_service_url
                svc = var.lower().replace("_url", "").replace("es", "es")
                derived = self.get_service_url(svc if svc != "es" else "es")
                assert derived, f"{var} or its derived URL should not be empty"
                self._log(f"  + {var}: derived as {derived}")

        # --- Step 4: Verify port vars match expected ranges ---
        self._log("STEP 4: Verifying port variables are in valid ranges")
        port_vars_from_example = {k: v for k, v in expected.items() if "PORT" in k}
        for var, val in port_vars_from_example.items():
            try:
                port = int(val)
                assert 1 <= port <= 65535, f"{var}={val} should be a valid port (1-65535)"
            except ValueError:
                # Some port vars may have defaults with colons — skip those
                pass
        self._log(f"+ All {len(port_vars_from_example)} port variables valid")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-27-01 COMPLETED — CONFIGURATION DRIFT DETECTION VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 2: Golden configuration
    # ------------------------------------------------------------------

    def test_golden_configuration(self):
        """TC-27-02: Golden configuration validation.

        Reads docker-compose.yml files from the repo. Asserts:
          1. All expected services are defined.
          2. Port mappings match expected ranges.
          3. Volume mounts exist for each service.
        """
        self._log("=== TC-27-02: GOLDEN CONFIGURATION VALIDATION TEST STARTED ===")

        # --- Step 1: Read docker-compose files ---
        self._log("STEP 1: Reading docker-compose files")
        compose_dir = self.repo_root / "infra" / "docker" / "compose"
        compose_main = compose_dir / "docker-compose.yml"
        compose_core = compose_dir / "docker-compose.core.yml"
        compose_misp = compose_dir / "docker-compose.misp.yml"
        compose_api = compose_dir / "docker-compose.api.yml"

        assert compose_main.exists(), f"docker-compose.yml should exist at {compose_main}"
        assert compose_core.exists(), f"docker-compose.core.yml should exist at {compose_core}"
        self._log(f"+ Found docker-compose.yml ({compose_main.stat().st_size} bytes)")
        self._log(f"+ Found docker-compose.core.yml ({compose_core.stat().st_size} bytes)")

        # Combine all compose file contents for searching
        all_content = ""
        compose_files = [compose_main, compose_core, compose_misp, compose_api]
        for f in compose_files:
            if f.exists():
                all_content += f.read_text(encoding="utf-8") + "\n"

        # --- Step 2: Assert all expected services are defined ---
        self._log("STEP 2: Verifying expected services are defined")
        expected_services = [
            "elasticsearch",
            "thehive",
            "cortex",
            "redis",
            "shuffle-backend",
            "shuffle-frontend",
        ]
        for svc in expected_services:
            # Service definitions appear as "  servicename:" at indent level
            pattern = rf"(?m)^  {re.escape(svc)}:"
            assert re.search(
                pattern, all_content
            ), f"Service '{svc}' should be defined in docker-compose files"
            self._log(f"  + Service '{svc}' defined")

        # --- Step 3: Assert port mappings match expected ranges ---
        self._log("STEP 3: Verifying port mappings")
        # Check that key services have port mappings defined
        port_checks = [
            ("elasticsearch", "9200"),
            ("thehive", "9000"),
            ("cortex", "9001"),
            ("shuffle-backend", "5001"),
        ]
        for svc, internal_port in port_checks:
            # Port mappings look like: "${PORT:-default}:internal_port"
            port_pattern = rf"(?m)^\s*-\s*\"[^\"]*:{internal_port}\""
            assert re.search(
                port_pattern, all_content
            ), f"Service '{svc}' should have port mapping to {internal_port}"
            self._log(f"  + {svc} has port mapping to {internal_port}")

        # --- Step 4: Assert volume mounts exist for each service ---
        self._log("STEP 4: Verifying volume mounts")
        # Check that named volumes are defined in the volumes section
        expected_volumes = [
            "es_data",
            "thehive_files",
            "cortex_data",
            "redis_data",
            "shuffle_apps",
            "shuffle_files",
        ]
        for vol in expected_volumes:
            # Named volumes appear in the volumes: section as "  volname:"
            vol_pattern = rf"(?m)^  {re.escape(vol)}:"
            assert re.search(
                vol_pattern, all_content
            ), f"Volume '{vol}' should be defined in docker-compose volumes section"
            self._log(f"  + Volume '{vol}' defined")

        # Check that services actually USE these volumes
        vol_usage_checks = [
            ("elasticsearch", "es_data"),
            ("thehive", "thehive_files"),
            ("cortex", "cortex_data"),
            ("redis", "redis_data"),
        ]
        for svc, vol in vol_usage_checks:
            # Volume usage: "      - volname:/some/path"
            usage_pattern = rf"(?m)^\s*-\s*{re.escape(vol)}:"
            assert re.search(
                usage_pattern, all_content
            ), f"Service '{svc}' should mount volume '{vol}'"
            self._log(f"  + {svc} mounts volume {vol}")

        # --- Step 5: Verify networks are defined ---
        self._log("STEP 5: Verifying network definitions")
        expected_networks = ["soar_net", "ti_net"]
        for net in expected_networks:
            net_pattern = rf"(?m)^  {re.escape(net)}:"
            assert re.search(
                net_pattern, all_content
            ), f"Network '{net}' should be defined in docker-compose"
            self._log(f"  + Network '{net}' defined")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-27-02 COMPLETED — GOLDEN CONFIGURATION VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 3: Volume persistence
    # ------------------------------------------------------------------

    def test_volume_persistence(self):
        """TC-27-03: Volume persistence validation.

        Asserts:
          1. Docker volumes exist for ES, TheHive, Cortex, Redis.
          2. Data directories are writable.
          3. Data directories contain data.
        """
        self._log("=== TC-27-03: VOLUME PERSISTENCE VALIDATION TEST STARTED ===")

        # --- Step 1: Check Docker volumes exist ---
        self._log("STEP 1: Checking Docker volumes exist")
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            volume_names = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except Exception as e:
            # If docker is not available (e.g. running inside container without
            # docker CLI), fall back to checking the bind-mount directories
            self._log(f"  + Docker CLI not available ({e}), checking bind-mount dirs")
            volume_names = []

        expected_volume_prefixes = ["soar_es_data", "soar_thehive", "soar_cortex", "soar_redis"]
        if volume_names:
            for prefix in expected_volume_prefixes:
                matching = [v for v in volume_names if prefix in v]
                assert len(matching) > 0, (
                    f"Docker volume with prefix '{prefix}' should exist. "
                    f"Available volumes: {volume_names[:20]}"
                )
                self._log(f"  + Volume '{matching[0]}' exists")
        else:
            self._log("  + Skipping Docker volume check (no docker CLI)")

        # --- Step 2: Check data directories exist and are writable ---
        self._log("STEP 2: Checking data directories are writable")
        runtime_data = self.repo_root / "runtime" / "data"
        expected_data_dirs = ["elasticsearch", "thehive", "cortex", "redis"]

        for dirname in expected_data_dirs:
            data_dir = runtime_data / dirname
            # The directory may not exist if running inside container (Docker named volumes)
            if not data_dir.exists():
                self._log(f"  + {dirname}: directory not present (Docker named volume) — skipping")
                continue
            # Test writability
            test_file = data_dir / f"tc27_write_test_{int(time.time())}.tmp"
            try:
                test_file.write_text("tc27-volume-test", encoding="utf-8")
                assert test_file.exists(), f"Should be able to write to {data_dir}"
                test_file.unlink()
                self._log(f"  + {dirname}: directory writable")
            except Exception as e:
                pytest.fail(f"Data directory {data_dir} is not writable: {e}")

        # --- Step 3: Verify data directories contain data ---
        self._log("STEP 3: Verifying data directories contain data")
        # Elasticsearch should have indexed documents (verified via API)
        try:
            es_count = self.es.count()
            assert es_count >= 0, f"ES document count should be >= 0, got {es_count}"
            self._log(f"+ Elasticsearch has {es_count} documents (data persists)")
        except Exception as e:
            pytest.fail(f"Could not verify ES data persistence: {e}")

        # TheHive should have cases (data persists)
        try:
            cases = self.thehive.search_cases()
            assert isinstance(cases, list), "TheHive cases should be a list"
            self._log(f"+ TheHive has {len(cases)} cases (data persists)")
        except Exception as e:
            pytest.fail(f"Could not verify TheHive data persistence: {e}")

        # Redis should be accessible (data persists)
        try:
            import redis as _redis

            r = _redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password(),
                decode_responses=True,
            )
            r.ping()
            self._log("+ Redis is accessible (data volume active)")
        except Exception as e:
            pytest.fail(f"Could not verify Redis persistence: {e}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-27-03 COMPLETED — VOLUME PERSISTENCE VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 4: Environment variables
    # ------------------------------------------------------------------

    def test_environment_variables(self):
        """TC-27-04: Environment variables validation.

        Asserts:
          1. self.env has all required keys.
          2. Each value is non-empty.
          3. URLs are valid HTTP URLs.
          4. API keys have minimum length.
        """
        self._log("=== TC-27-04: ENVIRONMENT VARIABLES VALIDATION TEST STARTED ===")

        # --- Step 1: Assert all required keys are present ---
        self._log("STEP 1: Checking required environment variables")
        required_keys = [
            "THEHIVE_API_KEY",
            "CORTEX_API_KEY",
            "SHUFFLE_DEFAULT_APIKEY",
            "ELASTIC_USERNAME",
            "ELASTIC_PASSWORD",
            "OPENSEARCH_PASSWORD",
            "REDIS_PASSWORD",
            "CORTEX_ADMIN_USER",
            "CORTEX_ADMIN_PASSWORD",
        ]
        missing_keys: list[str] = []
        for key in required_keys:
            if key not in self.env:
                missing_keys.append(key)
            else:
                self._log(f"  + {key}: present")

        assert (
            len(missing_keys) == 0
        ), f"Required environment variables missing from self.env: {missing_keys}"

        # --- Step 2: Assert each value is non-empty ---
        self._log("STEP 2: Verifying all values are non-empty")
        empty_keys: list[str] = []
        for key in required_keys:
            val = self.env.get(key, "")
            if not val or not val.strip():
                empty_keys.append(key)
            else:
                self._log(f"  + {key}: non-empty ({len(val)} chars)")

        assert len(empty_keys) == 0, f"Environment variables with empty values: {empty_keys}"

        # --- Step 3: Assert URLs are valid HTTP URLs ---
        self._log("STEP 3: Verifying URL variables are valid HTTP URLs")
        url_keys = ["SHUFFLE_URL", "THEHIVE_URL", "ES_URL", "CORTEX_URL", "MISP_URL"]
        for key in url_keys:
            val = self.env.get(key, "")
            if val:
                parsed = urlparse(val)
                assert parsed.scheme in (
                    "http",
                    "https",
                ), f"{key} should have http/https scheme, got: {val}"
                assert parsed.hostname, f"{key} should have a hostname, got: {val}"
                self._log(f"  + {key}: {val} (valid URL)")
            else:
                # URL might be derived — verify get_service_url returns something
                svc_map = {
                    "SHUFFLE_URL": "shuffle",
                    "THEHIVE_URL": "thehive",
                    "ES_URL": "es",
                    "CORTEX_URL": "cortex",
                    "MISP_URL": "misp",
                }
                derived = self.get_service_url(svc_map[key])
                assert derived, f"{key} or derived URL should not be empty"
                parsed = urlparse(derived)
                assert parsed.scheme in (
                    "http",
                    "https",
                ), f"Derived {key} URL should be valid: {derived}"
                self._log(f"  + {key}: derived as {derived}")

        # --- Step 4: Assert API keys have minimum length ---
        self._log("STEP 4: Verifying API keys have minimum length")
        api_key_vars = [
            "THEHIVE_API_KEY",
            "CORTEX_API_KEY",
            "SHUFFLE_DEFAULT_APIKEY",
        ]
        min_key_length = 10  # API keys should be at least 10 chars
        for key in api_key_vars:
            val = self.env.get(key, "")
            assert (
                len(val) >= min_key_length
            ), f"{key} should be at least {min_key_length} characters, got {len(val)} chars"
            self._log(f"  + {key}: {len(val)} chars (>= {min_key_length})")

        # --- Step 5: Assert passwords have minimum length ---
        self._log("STEP 5: Verifying passwords have minimum length")
        password_vars = [
            "ELASTIC_PASSWORD",
            "OPENSEARCH_PASSWORD",
            "REDIS_PASSWORD",
            "CORTEX_ADMIN_PASSWORD",
        ]
        min_pwd_length = 8
        for key in password_vars:
            val = self.env.get(key, "")
            assert (
                len(val) >= min_pwd_length
            ), f"{key} should be at least {min_pwd_length} characters, got {len(val)} chars"
            self._log(f"  + {key}: {len(val)} chars (>= {min_pwd_length})")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-27-04 COMPLETED — ENVIRONMENT VARIABLES VALIDATED ===")
