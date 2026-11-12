# Webhook backlog 9.5 — evidence matrix

| Requirement | Risk | Implementation | Tests | Framework |
|---|---|---|---|---|
| Canonical severity 0..4 | Silent drop (B3) | `domain/severity.py` + `normalize_inputs.py` mirror | `tests/contract/test_alert_contract.py` | OWASP API10 |
| schema_version pinning | Contract drift | `contracts/*.schema.json`, schema validator | contract tests | OWASP API9 |
| Workflow verdict | Transport≠processing | `POST /api/v1/alerts/callback` + `record_workflow_verdict` | `test_alert_contract`, worker tests | NIST RS |
| HMAC transport sig | Tamper/replay | `security/webhook_signing.py` `verify_request` | `test_webhook_signing.py` (15 cases) | ISO A.8.28, OWASP API2 |
| HMAC envelope sig | Tamper (hook no-headers) | `sign_envelope` + `normalize_inputs` verify | signing + contract tests | OWASP API10 |
| Anti-replay nonce | Replay | RedisNonceStore SET NX EX (fail-closed) | `test_nonce_replay_rejected` | OWASP API2 |
| Scoped service tokens | Privilege escalation | `_SCOPE_RULES` in `auth.py` | scope deny tests | ISO A.5.17 |
| No INTERNAL in workflow | Secret sprawl | `workflow_actions.py` uses scoped tokens | grep gate in CI | ISO A.5.17 |
| JWT no-role | Privilege escalation | missing role -> READONLY | auth matrix tests | OWASP API5 |
| Pre-parse body cap | DoS (API4) | `BodyLimitMiddleware` | `test_alert_contract` (bounds) | OWASP API4 |
| Pre-auth rate limit | Brute force | `PreAuthRateLimitMiddleware` before auth | middleware tests | OWASP API4 |
| Error redaction | Capability URL leak (B6) | `security/redaction.py` + structured codes | `test_redaction.py` | ISO A.8.15 |
| enqueue_failed + reconciler | Orphan record (B4) | compensation in `admit` + `reconcile()` | `test_alert_admission.py` | NIST RC |
| Phantom binding repair | Fake admission (B5) | CAS unbind + re-claim | admission tests | NIST RC |
| Idempotency collision | Payload swap | fingerprint compare -> 409 | admission tests | OWASP API3 |
| gather isolation | Sibling task loss | `return_exceptions=True` | worker tests | NIST RS |
| retry policy by class | Retry storm/never | `error_code`+`retryable` from forward | worker tests | NIST RS |
| Log injection guard | Forged Loki lines (CWE-117) | `_log_safe` in grafana receiver | grafana tests | ISO A.8.15 |
| IP/hostname validation | URL/LogQL injection | schema validators + `*_enc` fields | contract tests | OWASP API10 |
| Sanitizer wired | Stored XSS/docs claim | `to_alert_dict` sanitizes free-text | `TestSanitizerWired` | ASVS V5 |
| CORS guard | Misconfig (API8) | wildcard+credentials dropped unless `CORS_ALLOW_ANY` | main wiring | OWASP API8 |
| Coverage gate | Untested security | `check_critical_coverage.py` >=95% modules | `make test-coverage-critical` | — |
| Collect gate | Broken suite (B1) | `test-collect` + httpx dep in extras | `make test-collect` | — |
| Env isolation | Leaky test (B2) | `_clean_env` in `test_webhook.py` | suite green in container | — |

Residual risks (documented, accepted for lab):
- Scoped tokens still embedded in workflow definition (no secret store
  in Shuffle); mitigated by scope + CIDR + rotation.
- Nonce store fail-closed only in Redis mode; in-memory store is
  per-process (single replica lab).
- At-least-once residual: one re-forward possible after committed
  forward + lost store write (dedup-bounded).
