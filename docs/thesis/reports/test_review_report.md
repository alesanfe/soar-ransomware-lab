# Test Review Report — SOAR Ransomware Lab

Generated: **2026-08-24 10:14:07 UTC**
Methodology: 7-dimension structured test review

---

## Overall Score

| Dimension | Score | Status |
|-----------|-------|--------|
| D2 Mutation | — | Not available |
| D3 Pyramid | 94.3 | Excellent |
| D4 Health | 99.5 | Excellent |
| D5 Isolation | 97.5 | Excellent |
| D6 Complexity | 83.4 | Good |
| D7 Duplication | 86.4 | Good |
| **Overall** | **92.2** | **Excellent** |


---

## D1 — Structural Coverage

> ⚠️ coverage.xml not found. Run with --with-coverage.


---

## D2 — Logic Coverage (Mutation Testing)

> ⚠️ Not available
> Run `make mutation` inside Docker to generate mutation testing data.


---

## D3 — Test Pyramid

- **Total tests**: 2041
- **Pyramid score**: 94.3/100 (deviation: 5.7%)

### Distribution by layer

| Layer | Tests | Actual % | Ideal % |
|-------|-------|----------|---------|
| Unit (unit + atomic) | 1346 | 65.9% | 70% |
| Integration | 336 | 16.5% | 20% |
| E2E | 281 | 13.8% | 10% |
| Other | 78 | 3.8% | — |

### Distribution by category

| Category | Files | Tests |
|----------|-------|-------|
| architecture | 1 | 1 |
| atomic | 4 | 101 |
| e2e | 49 | 281 |
| general | 2 | 20 |
| integration | 30 | 336 |
| performance | 4 | 30 |
| security | 1 | 27 |
| unit | 79 | 1245 |


---

## D4 — Test Health

- **Skipped tests**: 2
- **XFail tests**: 0
- **Files with skips**: 2

_Static analysis via AST/regex — only `@pytest.mark.skip` and `pytest.skip()` calls are detected. Conditional skips inside test bodies may not be counted._

### Top skip reasons

| Reason | Count |
|--------|-------|
| Tenzir REST API not available (404 on /api/v0/status) | 1 |
| docker compose not available inside container — test requires host execution | 1 |


---

## D5 — Test Isolation

- **Requires Docker**: 35 tests in 3 files
- **Requires external services**: 83 tests in 9 files

### Files requiring Docker

- `tests/integration/test_docker_partial_failure.py`
- `tests/integration/test_docker_runtime_status.py`
- `tests/integration/test_smoke.py`

### Files requiring external services

- `tests/integration/test_api_init.py`
- `tests/integration/test_app_e2e.py`
- `tests/integration/test_data_consistency.py`
- `tests/integration/test_elasticsearch_integration.py`
- `tests/integration/test_idempotency.py`
- `tests/integration/test_openapi_spec_sync.py`
- `tests/integration/test_race_conditions.py`
- `tests/performance/test_database_performance.py`
- `tests/performance/test_workflow_performance.py`


---

## D6 — Test Complexity

- **Long tests (>50 lines)**: 169
- **Weak tests (<1.5 assertions avg)**: 60

### Top 10 longest test functions

| Test | File | Line | Length |
|------|------|------|--------|
| `test_realistic_ransomware` | `tests/e2e/TC-09/test_realistic_ransomware.py` | 49 | 224 |
| `test_mttr_percentiles` | `tests/e2e/TC-KPI-02/test_mttr_percentiles.py` | 114 | 208 |
| `test_concurrent_alerts` | `tests/e2e/TC-05/test_concurrent_alerts.py` | 195 | 172 |
| `test_golden_thread_integrity` | `tests/e2e/TC-32/test_golden_thread.py` | 49 | 152 |
| `test_ioc_analysis_time` | `tests/e2e/TC-32/test_ioc_analysis_time.py` | 108 | 143 |
| `test_critical_severity` | `tests/e2e/TC-06/test_critical_severity.py` | 35 | 138 |
| `test_node_timings` | `tests/e2e/TC-KPI-05/test_node_timings.py` | 38 | 132 |
| `test_polymorphic_behavior` | `tests/e2e/TC-25/test_behavioral_detection.py` | 61 | 131 |
| `test_duplicate_prevention` | `tests/e2e/TC-26/test_extreme_load.py` | 487 | 126 |
| `test_least_privilege` | `tests/e2e/TC-20/test_zero_trust.py` | 237 | 123 |

### Files with low assertion density (potential weak tests)

| File | Tests | Assertions | Avg/test |
|------|-------|------------|----------|
| `tests/unit/integrations/test_send_alert.py` | 5 | 2 | 0.4 |
| `tests/unit/common/test_timeout_handling.py` | 10 | 5 | 0.5 |
| `tests/atomic/test_alert_validation.py` | 21 | 14 | 0.7 |
| `tests/integration/test_cortex_integration.py` | 3 | 2 | 0.7 |
| `tests/integration/test_external_service_failure.py` | 15 | 10 | 0.7 |
| `tests/unit/services/test_auth_service.py` | 16 | 11 | 0.7 |
| `tests/integration/test_shuffle_integration.py` | 4 | 3 | 0.8 |
| `tests/integration/test_thehive_integration.py` | 4 | 3 | 0.8 |
| `tests/unit/api/test_api_auth.py` | 4 | 3 | 0.8 |
| `tests/unit/clients/test_shuffle_client.py` | 27 | 22 | 0.8 |

_Static analysis via AST — assertion counts are based on `assert` statements in the source code, not runtime execution._


---

## D7 — Test Duplication

- **Unique test names**: 1947
- **Duplicated names**: 88

### Duplicated test names

| Test name | Files |
|-----------|-------|
| `test_alert` | `tests/integration/test_api_endpoints.py`, `tests/integration/test_data_consistency.py`, `tests/integration/test_idempotency.py` +1 more |
| `test_audit_trail` | `tests/e2e/TC-02/test_benign.py`, `tests/e2e/TC-21/test_forensic.py`, `tests/e2e/TC-31/test_compliance.py` |
| `test_case_creation` | `tests/e2e/TC-09/test_realistic_ransomware.py`, `tests/unit/domain/test_domain_models.py` |
| `test_circuit_breaker_closes_on_success` | `tests/integration/test_external_service_failure.py`, `tests/unit/common/test_circuit_breaker.py` |
| `test_circuit_breaker_opens_on_failures` | `tests/integration/test_external_service_failure.py`, `tests/unit/common/test_circuit_breaker.py` |
| `test_clear` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/domain/test_in_memory_storage.py` |
| `test_concurrent_alerts` | `tests/e2e/TC-04/test_performance.py`, `tests/e2e/TC-05/test_concurrent_alerts.py` |
| `test_connection_and_authentication` | `tests/integration/test_elasticsearch_integration.py`, `tests/integration/test_misp_integration.py` |
| `test_count_alerts` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/infrastructure/test_sqlite_alert_repository.py` |
| `test_count_alerts_by_status` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/infrastructure/test_sqlite_alert_repository.py` |
| `test_count_backups_by_status` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/infrastructure/test_sqlite_alert_repository.py` |
| `test_count_cases` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/infrastructure/test_sqlite_alert_repository.py` |
| `test_count_cases_by_status` | `tests/unit/domain/test_in_memory_alert_repository.py`, `tests/unit/infrastructure/test_sqlite_alert_repository.py` |
| `test_create_app_returns_fastapi` | `tests/unit/api/test_api_composition.py`, `tests/unit/api/test_api_main.py` |
| `test_create_backup_success` | `tests/unit/api/test_api_main.py`, `tests/unit/services/test_backup_service.py` |

_Showing 15 of 88 duplicated names._


---

## Recommendations

- ✅ **D3 Pyramid**: Distribution is close to ideal (deviation: 5.7%).
- ✅ **D4 Health**: Only 2 skipped tests.
- ✅ **D5 Isolation**: 35 tests require Docker (1.7%).
- ⚠️ **D6 Complexity**: 169 tests are >50 lines. Consider refactoring into smaller tests.
- ⚠️ **D6 Complexity**: 60 files have low assertion density (<1.5 avg). Add more assertions to strengthen tests.
- ⚠️ **D7 Duplication**: 88 test names are duplicated across files. Consider renaming for clarity.
- ℹ️ **D1 Coverage**: Run with `--with-coverage` to analyze structural coverage.
- ℹ️ **D2 Mutation**: Run `make mutation` in Docker to analyze logic coverage.


---

## Methodology

This report evaluates the test suite across 7 dimensions:

| Dimension | What it measures | Ideal | Tool |
|-----------|------------------|-------|------|
| D1 — Structural coverage | % of code lines/branches executed | ≥80% line, ≥70% branch | coverage.py |
| D2 — Logic coverage (mutation) | % of mutations killed by tests | ≥90% | mutmut |
| D3 — Test pyramid | Proportion unit/integration/e2e | 70/20/10 | AST analysis |
| D4 — Test health | Skipped, xfail, flaky tests | <5% skipped | AST + regex |
| D5 — Isolation | Tests depending on Docker/external | <30% Docker | pytest markers |
| D6 — Complexity | Long tests, low assertion density | <10 long, >2 avg assertions | AST analysis |
| D7 — Duplication | Duplicated test names | 0 duplicates | AST analysis |

### Scoring

Each dimension produces a 0-100 score. The overall score is the arithmetic mean.
Dimensions D1 and D2 are optional (require external data sources).
