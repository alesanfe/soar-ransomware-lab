# Evaluación PKI / Secretos — ISO 27001 A.8 · NIST SP 800-57 · OWASP Secrets Management

> **Fecha**: 2026-11-12 · Re-evaluación bajo frameworks criptográficos (complementa `docs/38`, ISO 25010/RFC 5280). **Resultado**: 2 defectos corregidos + 1 hallazgo crítico **documentado como deuda aceptada de lab** (decisión del propietario). Score ~9.3/10.

## Hallazgo crítico — secretos reales trackeados en GitHub (ACEPTADO por decisión)

`.env.full` (~32 secretos vivos: ELASTIC/THEHIVE/CORTEX/REDIS/MISP) y `.env.testing` (~12) están **trackeados y pusheados a `origin/main`** — commiteados antes de la regla `.gitignore` (que no aplica retroactivamente). Decisión del propietario: deuda aceptada de lab — los secretos protegen solo el laboratorio local; la remediación documentada es `make rotate-secrets` + `git rm --cached` cuando se decida ejecutarla.

**Contención aplicada**: gate `test_no_new_env_files_tracked` — cualquier **nuevo** archivo de secretos que quede trackeado rompe la suite (git `ls-files` con fallback a parseo de `.git/index` DIRC; skip documentado si no hay fuente — enforced en CI/host). El radio de explosión queda pineado a los 3 archivos conocidos.

## Defectos corregidos

| ID | Defecto | Fix | Gate |
|----|---------|-----|------|
| PKI-EVAL-2-01 | **Rotaciones sin rastro persistente** — `rotate_secrets.py` reportaba solo a stdout: sin evidencia de qué se rotó y cuándo (A.8.15, OWASP auditing) | `write_audit_record()` → JSONL append-only en `runtime/secrets-rotation.audit.jsonl` (gitignored): timestamp, vars, rotated/manual/failed — **nunca valores** | `test_rotation_writes_persistent_audit_record` |
| PKI-EVAL-2-02 | **`.env.full`/`.env.container` escritos con umask por defecto** — en hosts POSIX los secretos quedaban group/world-readable (0644) | `_chmod_600()` best-effort tras cada escritura en `env_files.py` (no-op seguro en NTFS) | `test_env_files_chmod_600_after_write` |

## Matriz por dimensión

| Dimensión | Marco | Estado verificado |
|-----------|-------|-------------------|
| **Rotación** | 800-57 §5.3 | `rotate_secrets.py` 7 fases (live-API → ALTER → env-only → sync → recreate → post-sync → **probes negativos**: la key vieja debe dar 401) + audit trail ahora persistente. Cert rotation: `make certs` regen manual documentada |
| **Almacenamiento** | A.8.24, 800-57 §6 | `ca.key` **nunca montado**, `chmod 600` en todas las keys, `*.key`+`.env*` gitignored, mounts `.key` forzados `:ro` (gate), env files ahora `chmod 600` post-write |
| **Expiración** | 800-57 §5.3.5 | Certs 365d + `probe_ssl_earliest_cert_expiry` ×10 endpoints + alertas 30d/14d (eval 38). Passwords/API keys sin expiry forzado — cadencia manual documentada |
| **Confianza CA** | 800-57 §6.2 | CA pineada `ca.crt` montada `:ro` por servicio · **PKI dual**: CA interna ≠ CA edge · probes TLS verifican contra CA pineada (handshake real, no TCP) · truststore JKS solo certs públicos |
| **Auditoría** | A.8.15 | ✅ Corregido — rotación deja JSONL append-only (PKI-EVAL-2-01) + `inventory_secrets.py` clasifica REAL/SYNTHETIC/PLACEHOLDER sin valores + `scan_secrets.py` en CI |
| **Distribución certs** | A.8.24 | **Verificado: cada servicio monta solo su `.key`+`.crt`+`ca.crt`, todo `:ro`** — sin mounts de directorio completo; ningún servicio puede leer claves ajenas |

## Positivos adicionales (bajo estos marcos)

- CSPRNG `secrets.SystemRandom` en toda generación (gate) · `${VAR:?}` fail-closed en compose
- CA RSA-4096 `CA:TRUE+keyCertSign/cRLSign`; servicios RSA-2048 con EKU serverAuth/clientAuth correctos
- Inventario sin fugas + scan en CI + placeholders auto-descriptivos distinguibles de secretos reales (gate)

## Residuales (justificados / deuda aceptada)

| Restricción | Naturaleza |
|-------------|------------|
| **Secretos vivos en historial GitHub** | Deuda aceptada por el propietario — lab sin datos reales; remediación documentada (`git rm --cached` + rotación total) |
| Sin CRL/OCSP en la CA | Lab: el compromiso se remedia re-emitiendo certs (superficie local); `cRLSign` presente por si se habilita |
| Rotación de certs manual | Procedimiento documentado; expiración monitorizada 30/14d da margen |
| Passwords sin expiración forzada | Lab: cadencia manual vía `make rotate-secrets` |

## Regresión

`test_pki_secrets.py`: 16 → **19 gates** (18 pass + 1 skip documentado en contenedor; en host/CI: 19/19).
