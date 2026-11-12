# Architecture Decision Records

Registro de decisiones arquitectónicas **tomadas y verificadas en código** —
no aspiracionales. Cada ADR enlaza el BUG/commit que lo materializó.

| ADR | Decisión | Estado |
| ----- | ---------- | -------- |
| [0001](0001-single-composition-root.md) | Composition root único | Aceptado (BUG-113) |
| [0002](0002-default-deny-auth-rbac.md) | Auth default-deny + RBAC por rutas | Aceptado (AUTH-001/003) |
| [0003](0003-atomic-idempotency-fingerprint.md) | Idempotencia atómica SET NX + fingerprint SHA-256 | Aceptado (IDEMP-001/002) |
| [0004](0004-rate-limit-pluggable-backend.md) | Rate limiter con backend intercambiable | Aceptado (BUG-134) |
| [0005](0005-tls-verify-on-by-default.md) | Verificación TLS ON por defecto | Aceptado (BUG-110) |
| [0006](0006-sqlite-wal-busy-timeout.md) | SQLite con WAL + busy_timeout | Aceptado (EPIC-2) |
| [0007](0007-fail-open-limiter-fail-closed-auth.md) | Fail-open limiter / fail-closed auth | Aceptado |
| [0008](0008-pooled-http-sessions.md) | Sesiones HTTP pooled con lifecycle explícito | Aceptado (BUG-122/127) |
| [0009](0009-mono-stack-http-registry.md) | Stack HTTP único + registro declarativo de adaptadores | Aceptado (D2/A2) |
| [0010](0010-thehive-legacy.md) | TheHive 3.5.2 legacy — riesgo aceptado y acotado | Superseded (TH-001 → TheHive 5.7.8-1) |
| [0011](0011-taxii-lite-scope.md) | TAXII-lite read-only sobre STIX (no servidor completo) | Aceptado (INT-01) |
| [0012](0012-single-node-opensearch.md) | OpenSearch single-node — limitación estructural | Aceptado |
| [0013](0013-uvicorn-workers.md) | Uvicorn multi-worker opt-in con stores Redis compartidos | Aceptado |
| [0014](0014-observability-stack-hardening.md) | S3 IAM por componente, s3-init fail-closed, OTel memory-limited, renderer TLS residual, excepciones de capacidades | Aceptado |
