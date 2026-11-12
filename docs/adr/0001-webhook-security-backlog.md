# ADR-001: Webhook security & reliability decisions (backlog 9.5)

Status: accepted (2026-11). Scope: alert admission pipeline
API ingest -> Redis Streams -> worker -> Shuffle hook, plus Grafana
receiver and workflow callbacks.

## Decisions

### D1. Canonical severity contract (CONTRACT-001)
One table `src/soar_lab/domain/severity.py` (0..4 + names), mirrored in
`normalize_inputs.py`. Absent severity -> documented default `medium(2)`.
TheHive's 1..3 mapping is applied at case-build time via
`severity_to_thehive`, never at admission. Closes B3.

### D2. Delivery vs processing (CONTRACT-004)
`forwarded` = transport 2xx, NOT workflow acceptance. The workflow
reports its verdict via signed `POST /api/v1/alerts/callback`
(`callback` scope) -> `workflow_accepted`/`workflow_rejected`.

### D3. Message signatures (HMAC-001)
* API->Shuffle: body-embedded `security` envelope (HMAC-SHA256 over
  canonical payload + timestamp + nonce + key_id) — Shuffle hooks do
  not forward HTTP headers to workflows, so transport headers cannot
  be used there.
* Shuffle->API: `X-SOAR-*` transport headers over
  `METHOD
PATH
TS
NONCE
SHA256(body)` verified by
  `webhook_signing.verify_request`.
* Different keys per direction; `*_PREV` slots for rotation grace;
  nonces in Redis SET NX EX (fail-closed), in-memory for tests.

### D4. Least-privilege service identities (AUTH-001/002)
`internal`, `webhook`, `callback`, `containment`, `cache`, `metrics`
scopes; INTERNAL token no longer embedded in workflow definitions.
Residual: scoped tokens still embedded (Shuffle cannot reference a
secret store) — mitigated by scope confinement + CIDR + rotation
slots. Vault/Docker-Secrets integration deferred (lab).

### D5. Admission atomicity — compensation, not Outbox (ADMISSION-001B)
store.create() -> queue.enqueue() failure marks the record
`enqueue_failed` (visible, reconcilable) instead of stranded `queued`;
the leader-lease reconciler re-enqueues periodically. Phantom
idempotency bindings are repaired CAS-safely (B5). Same key +
different fingerprint -> 409 (IDEMP-004).

### D6. Fail-safe vs fail-open table (DOS-003, WORKER-003)
| Control | Backend failure policy |
|---|---|
| Post-auth rate limit | fail-open + warn (availability) |
| Pre-auth rate limit | in-process (no backend) |
| Nonce store | fail-closed 401 |
| Dedup on unreadable store | defer (pending), never forward |
| Idempotency binding | never silent-duplicate |
| Queue unavailable | enqueue_failed + 503 |

### D7. Pre-parse resource limits (DOS-001/002)
BodyLimitMiddleware counts bytes before JSON parse (413); per-prefix
budget via `WEBHOOK_PAYLOAD_MAX_SIZE` (now a real knob, CONFIG-001)
and global `REQUEST_BODY_MAX_BYTES`. Pre-auth per-IP sliding window
runs before DefaultDenyAuth so token guessing consumes budget.

### D8. Error redaction (ERROR-001/002)
`security/redaction.py` is the single policy: forward errors become
structured `{code, retryable}` — never `str(exc)` — so capability URLs
(`webhook_<uuid>`) can't reach last_error, metrics or DLQ (B6).

### D9. Log integrity (INPUT-003)
Grafana label values are control-char-escaped before logging
(CWE-117). Structured log fields preferred over interpolation.

### D10. At-least-once semantics (WORKER-002)
Duplicates are possible only between `forward OK` and `store.update`;
`_terminal_check` dedups reclaimed entries whose record is terminal.
When the store is unreadable the entry defers (pending) — never
re-POSTs blind. Documented residual: a store write lost *after* a
committed forward can re-forward once (bounded by dedup + idempotency
keys downstream).

## Consequences
Positive: no silent drops (B3), no phantom state (B4/B5), no URL/secret
leakage (B6), signed + replay-protected messages, least-privilege
identities, real config knobs.
Costs: workflow scripts carry scoped secrets (D4 residual); the
`enqueue_failed` state needs the reconciler (leader-elected) running;
severity enum extended with INFORMATIONAL=0.
