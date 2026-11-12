# Evaluación multi-marco — PKI y gestión de secretos

> Evaluación formal de la PKI interna y el ciclo de vida de secretos:
> `scripts/setup/gen_certs.sh` (CA + certs por servicio),
> `infra/docker/config/certs/`, `security/secret_generator.py`,
> `rotate_secrets.py`, `inventory_secrets.py`, `scan_secrets.py` y la
> monitorización de expiración de certificados. Metodología de
> `docs/32`-`37`: hallazgos verificados en vivo y pineados con gates
> (`tests/architecture/test_pki_secrets.py`, **16 gates**).
> Revisión 2026-11-11: **3 hallazgos** corregidos. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Seguridad/fiabilidad de la gestión criptográfica |
| NIST SP 800-57 | Tamaños de clave, periodos crypto, protección de clave privada |
| CWE-320 (gestión de claves), CWE-798 (credenciales) | Detección de secretos embebidos, defaults débiles |
| RFC 5280 | basicConstraints, keyUsage, EKU, SAN |
| SRE | Monitorización de expiración, rotación operativa |

## Evidencia de runtime (post-fix)

```
gen_certs --verify   15 certs lab-CA OK, 2 bundles externos skipped, exit 0
cert expiry probes   10 endpoints TLS con probe_ssl_earliest_cert_expiry
                     (antes 7) — opensearch/redis/shuffle-backend ~364d
CA                   RSA-4096, CA:TRUE+keyCertSign, validez 10 años
service certs        RSA-2048, 365d, SAN hostname+localhost+127.0.0.1
ca.key               NUNCA montado en contenedores (solo ca.crt público)
.env.full            secretos reales alta entropía (eF3S6ttX… NMtwOgbG…)
```

## Hallazgos corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| PKI-EVAL-001 | **`--verify` roto permanentemente** — el loop verificaba TODO `*.crt` incluyendo `ca-bundle.crt`/`debian-ca-plus-lab.crt` (CAs públicas → `error 18` → exit 1) | `openssl verify` en vivo | Filtro por issuer==CA-subject (RFC2253): solo certs emitidos por la CA del lab se verifican; bundles externos skipped explícitamente; gate `test_verify_filters_foreign_bundles` |
| PKI-EVAL-002 | **Expiración de certs sin monitorizar en 3/10 endpoints TLS** — opensearch:9200, redis:6379 y shuffle-backend:5443 no estaban en `blackbox-https` (los dos últimos sondeados con TCP plano: un listener TLS roto pasaría) | `probe_ssl_earliest_cert_expiry` solo cubría 7 instancias | Módulo `tcp_tls` (handshake TLS contra CA pineada, min TLS12) + job `blackbox-tls` → 10/10 endpoints con métrica de expiración; alertas obs_cert_expiry_30d/14d ahora cubren todo; 2 gates |
| PKI-EVAL-003 | **`make certs` en Windows no generaba la CA interna** — Makefile.win solo creaba el cert nginx `soar.local`; Makefile.linux además generaba `certs/misp` + `misp-full.pem` → setup Windows sin cert MISP | Diff de targets | Makefile.win ahora replica el flujo completo + targets `verify-certs`/`rotate-secrets`/`secrets-inventory` en ambos Makefiles (rotate_secrets.py e inventory_secrets.py no eran descubribles); 2 gates |

## Puntos positivos (verificados)

- **CA bien formada**: RSA-4096, `basicConstraints critical CA:TRUE`, `keyUsage keyCertSign+cRLSign`, 10 años; reutilización idempotente (no rota silenciosamente al añadir servicios).
- **Certs por servicio correctos**: RSA-2048, 365d, SAN `DNS:servicio + localhost + IP:127.0.0.1`, `keyUsage digitalSignature+keyEncipherment`, EKU `serverAuth`/`clientAuth` según rol — TLS 1.3 compatible (nota `keyUsage` documentada).
- **Claves protegidas**: `chmod 600`, `*.key` y `.env*` gitignored, `ca.key` jamás montado en contenedores, montajes `*.key` forzados `:ro` por gate.
- **Generación CSPRNG**: `secrets` (SystemRandom) en todo — sin `random.*` de propósito general.
- **Rotación operativa real**: `rotate_secrets.py` en 7 fases (API vivo → DB ALTER → env-only → sync → recreate → post-sync → verify con probes negativos), nunca imprime secretos, documenta lo no rotable (MISP_ENCRYPTION_KEY).
- **Inventario sin fugas**: `inventory_secrets.py` clasifica REAL/SYNTHETIC/PLACEHOLDER sin mostrar valores; `scan_secrets.py` ×2 + gate CI.
- **Expiración alertada**: `obs_cert_expiry_30d`/`_14d` con `min(probe_ssl_earliest_cert_expiry)` — ahora con cobertura completa.
- **PKI dual deliberada**: CA interna (servicios) + CA edge (nginx `soar.local`) separadas — el edge no firma material interno.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| CA de 10 años | Lab — rotación total requeriría re-emisión de los 15 certs; la expiración ya está monitorizada a 30/14d |
| Certs con `localhost`/`127.0.0.1` en SAN además del nombre de servicio | Facilita el acceso dual host/contenedor del lab; no amplía superficie real (el tráfico sigue interno) |
| Truststore JKS con password `changeit` | Convención Java — el truststore solo contiene certs públicos; el keystore con clave está montado `:ro` |
| Rotación de CA no automatizada | Procedimiento manual documentado (`delete certs dir` → regen); frecuencia esperada: años |
| `.env.example` con placeholders legibles | Auto-descriptivos por convención (nombre de var embebido) — gate nuevo los distingue de secretos reales |

## STRIDE de la PKI

| Amenaza | Control | Estado |
|---|---|---|
| Suplantación (cert falso) | CA pineada montada `:ro`; probes verifican contra ella | ✅ |
| Robo de clave | `ca.key` nunca montado, `chmod 600`, gitignored | ✅ |
| Expiración silenciosa | `probe_ssl_earliest_cert_expiry` ×10 + alertas 30d/14d | ✅ |
| Secretos débiles | CSPRNG + rotación + inventario + escaneo CI + compose `${VAR:?}` fail-closed | ✅ |
| Leak en ejemplos | gate `.env.example` sin secretos reales | ✅ |

## Regresión

- **16/16 gates** `test_pki_secrets.py`.
- **204/204** `tests/architecture/` totales.
- Vivo: `--verify` exit 0, 10 endpoints TLS con métrica de expiración, handshakes verificados.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Corrección PKI (RFC 5280) | 8.5 → **9.5** — verify funcional |
| Monitorización | 8.0 → **9.5** — cobertura expiración completa |
| Gestión de secretos | 9.0 → **9.5** |
| Operabilidad (targets/paridad) | 8.0 → **9.5** — Makefile.win paritario |
| Mantenibilidad | 8.5 → **9.5** — 16 gates |
| **Global** | ~8.4 → **~9.5** |
