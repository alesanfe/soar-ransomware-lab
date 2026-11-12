# 46 — Evaluación: core stack (ISO 27001 / CIS / NIST CSF)

> **Área**: Elasticsearch, OpenSearch, Redis, TheHive, Cortex, Shuffle (compose `core` + `main` + `opensearch` + overlay `hardened`).
> **Marcos**: ISO 27001:2022 A.8 (gestión de activos), A.12 (seguridad de operaciones), A.13 (seguridad en comunicaciones); CIS Controls v8 §4 (configuración segura), §5 (gestión de cuentas), §12 (infraestructura de red); NIST CSF PR.PS (Platform Security).
> **Resultado**: **~9,6/10** (re-evaluación profunda; la eval inicial del core quedó en ~9,5). 17 gates nuevos, 0 defectos nuevos activos — solo residuales ya documentados y justificados.

## 1. Matriz de cumplimiento

### TLS interno — ISO A.13.1 / CIS 12.3 / NIST PR.PS-1

| Servicio | Estado verificado | Evidencia |
|----------|------------------|-----------|
| Elasticsearch | TLS http + transport + `verification_mode=certificate` + xpack auth | `openssl s_client` → `Verify return code: 0`; `es-in:200` con `--cacert`+auth desde soar_api |
| OpenSearch | `plugins.security` activo, http+transport TLS con PEM lab-CA | `401` sin credenciales; ISM TLS verificado |
| Redis | **TLS-only** (`--port 0`, sin listener plano) + `requirepass` | `redis-cli --tls --cacert ping → PONG` (doctor OPS-EVAL-002) |
| TheHive | 9443 TLS lab-CA | `curl --cacert https://localhost:18100/ → 200` |
| Cortex | 9443 TLS lab-CA | `curl --cacert https://localhost:18101/ → 303` |
| Shuffle | backend TLS variant + ingress guard; OpenSearch con `SKIPSSL_VERIFY:-false` + CA montado | compose + gate |

PKI: CA propia (`infra/docker/config/certs/`, `gen_certs.sh`/`make certs`), SANs correctos, JKS con 162 CAs+lab-CA para JVM (TheHive). Quirk Schannel `CERT_TRUST_REVOCATION_STATUS_UNKNOWN` documentado (benigno, verificable con OpenSSL).

### Cifrado de datos — ISO A.8.1/A.10 / CIS 3.11

- **En tránsito**: 100% de los canales internos evaluados cifrados con la CA del lab (arriba).
- **En reposo**: volúmenes Docker sin cifrar a nivel FS — compensación documentada: lab de host único, BitLocker/host-encryption es el control a nivel plataforma; backups cifrados (eval backup/DR); Redis `--appendonly no --save ""` → **minimización**: no persiste datos en disco.
- Residual aceptado: sin LUKS/dm-crypt en volúmenes (fuera del alcance Docker Desktop/lab).

### Segmentación — ISO A.13.1 / CIS 12.2/12.4 / NIST PR.PS-5

- `soar_net` (10.100.0.0/16 fija) + **`ti_net` `internal: true`** → Redis/TheHive/Cortex/Shuffle/ES sin egress fuera del overlay.
- Egress guards (api_egress_guard, shuffle_backend_ingress_guard, network_watcher) — eval 39.
- **Exposición**: 20 puertos publicados, **todos `127.0.0.1:*`**, cero binds `0.0.0.0` (gate `test_no_public_port_binds`).

### Gestión de credenciales — ISO A.9.4/A.12.4 / CIS 5.1-5.3

- Expansión `:?required` en secretos críticos (`CORTEX_API_KEY`, `THEHIVE_SECRET`) → fail-fast en `make up` si faltan.
- `.env.full`/`.env.container` gitignored; exports GitOps de Shuffle scrubbean tokens a placeholders `__VAR__` + gate (TST-EVAL-001).
- Auth obligatoria en todos los datastores (ES 401 sin creds, OS security plugin, Redis requirepass+TLS, TheHive/Cortex API keys).
- `make rotate-secrets`/`verify-certs` como targets operacionales.
- Residual: secretos como env vars visibles en `docker inspect` (modelo elegido; docker secrets sería el endurecimiento alternativo — documentado).

### Alta disponibilidad — ISO A.12.1 / NIST PR.PS-1

Diseño single-node de laboratorio; el cumplimiento se mide en **resiliencia**, no replicación:

- `restart: unless-stopped` en todos los core; verificado involuntariamente: 41 contenedores auto-recuperaron tras caída de Docker Desktop.
- Resource limits + reservations en cada core (redis 0.5cpu/1G, shuffle 2.0/4G, ES Java heap 2g) → un servicio fugado no tumba el host.
- Rotación de logs `json-file 10m×3` universal.
- Backups + drills medidos (RTO ~94s), ISM/ILM de retención en OpenSearch/ES.
- Residual: sin réplicas/cluster — inaceptable en producción, correcto para lab reproducible.

### Healthchecks — ISO A.12.1.3 / NIST PR.PS-4

- **6/6 servicios core con healthcheck** (todos los 41 del stack lo tienen).
- Nivel de **aplicación**, no TCP: ES hace `curl --cacert -u elastic:` → `_cluster/health`; Shuffle `wget /api/v1/health`; start_periods realistas (ES 90s, Shuffle 180s).
- Redis `nc -z` a nivel puerto (aceptable para readiness; el probe TLS+auth real lo hace `doctor.py` tras OPS-EVAL-002).

### Hardening de contenedores — CIS 4.1/4.8 / NIST PR.PS-3

- Overlay `docker-compose.hardened.yml` **activo por defecto** en `make up` (`up-lab` opt-out explícito).
- 89 directivas: `cap_drop: [ALL]` ×11, `read_only: true` ×18, `no-new-privileges`, usuarios no-root (`redis`, `thehive`, `1000`, `65534`), seccomp por defecto en orborus.
- `docker-socket-proxy` con whitelist de verbs para api/network-watcher.
- Residual **SOAR-012 documentado**: cortex/shuffle-backend/orborus mantienen `docker.sock` RW — necesitan spawnear workers/analyzers; compensado con límites de recursos + `ti_net` interno.

### Gestión de vulnerabilidades — ISO A.12.6 / CIS 7.1-7.4

- **Trivy** en CI (`aquasecurity/trivy-action`, SHA-pinned) con upload SARIF a code-scanning.
- **ZAP DAST**: api-scan + baseline con `.zap/rules.tsv` comprometido.
- **pip-audit** de `requirements.lock` en suite quality (module-scoped, TST-EVAL-014) + `security_thresholds.yaml`.
- checkov/semgrep/bandit en `make lint`; Dependabot SHA/version updates.

## 2. Residuales cerrados en esta pasada

| Residual (antes) | Cierre |
|----------|---------------|
| ~~docker.sock RW en cortex/shuffle/orborus~~ | **Cerrado** — los 3 ya enrutaban por `DOCKER_HOST=tcp://docker-socket-proxy:2375` con `volumes: !override` que quita el mount; el comentario del overlay quedó stale y se corrigió. Gate nuevo lo hace cumplir. Orborus verificado operando la Docker API por el proxy (cleanup loop lista contenedores). |
| ~~Secretos en env vars (visibles en inspect)~~ | **Parcialmente cerrado** — Redis migrado a `secrets:` env-sourced + `--requirepass "$$(cat /run/secrets/redis_password)"`: `docker inspect` muestra el `$(cat …)` sin evaluar, cero literal en args. Verificado live: healthcheck nuevo PASS, `redis-cli --tls` PONG, cliente API `rediss://` ping OK. ES/OpenSearch/TheHive/Cortex mantienen env porque las imágenes no soportan `_FILE` — residual justificado. El patrón se extendió a `misp-db` (MariaDB `*_FILE` nativo, MISP-EVAL-011). |
| ~~Healthcheck Redis a nivel puerto~~ | **Cerrado** — healthcheck ahora `redis-cli --tls --cacert … ping` con auth real (leyendo el secret montado), no `nc -z`. Container reporta healthy tras recreate. |
| Sin cifrado de volúmenes en reposo | Fuera del alcance Docker Desktop (`Get-BitLockerVolume`/`manage-bde` requieren admin — no verificable desde la sesión); mitigado por no-persistencia Redis + backups cifrados. Recomendación documentada: activar cifrado de host. |
| Single-node sin réplicas | Lab reproducible; resiliencia cubierta por restart+healthchecks+DR medido. |

## 3. Regresión

- `tests/architecture/test_core_stack_controls.py`: **20/20** (TLS, secrets-as-files, healthcheck real, segmentación, resiliencia, hardening, proxy de spawners).
- Suite arquitectura total tras añadir el fichero: **292/292**.
