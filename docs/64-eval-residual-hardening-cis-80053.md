# 64 — Evaluación: endurecimiento residual (CIS / NIST 800-53 / ISO 27001)

**Fecha**: 2026-08-06 · **Alcance**: superficie de ataque transversal — compose (privilegios, usuarios, sockets), imágenes base, marcadores de deuda, credenciales por defecto, contenedores extra
**Marcos**: CIS Docker Benchmark 5.x, NIST SP 800-53 (CM-7 least functionality, AU audit, RA-5 vulnerability mgmt), ISO 27001 A.8.8 (gestión de vulnerabilidades técnicas)
**Veredicto**: **~9.6/10** — 1 defecto de posture de parcheo corregido (edge EOL), 5 gates nuevos

---

## 1. Resumen

Segunda evaluación del endurecimiento residual (la primera fue `docs/45-eval-residual-hardening.md`, de cierre de residuales locales CI/docs). Esta iteración hace un **barrido de superficie de ataque y deuda técnica transversal**: rama de las imágenes base, privilegios de contenedor, sockets crudos, marcadores de deuda en código y credenciales por defecto — el anexo de "residuales aceptados" de las 18 evaluaciones previas re-verificado contra evidencia viva.

## 2. Defecto corregido

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| RH-EVAL-2-001 | **Edge nginx en rama EOL** — `nginx:1.25-alpine` (mainline, sin soporte) en el componente más expuesto, mientras `apps/web-management` y `apps/docs-site` ya estaban en `1.27-alpine` digest-pinned (WEB-EVAL-007 dejó el edge atrás) | `NGINX_IMAGE` → `nginx:1.27-alpine` en 2 compose + 5 envs; pull + recreate + verify | `nginx/1.27.5` healthy · HTTPS 200 · `:80`→`301` |

## 3. Barrido de superficie — verificado limpio

| Vector | Resultado |
|--------|-----------|
| **Deuda en código** | **0 marcadores** `# TODO/FIXME/XXX/HACK` en `src/` — los hits eran literales de string (lista de patrones del scanner) y el término "deprecated" legítimo del versionado de API |
| **Privilegios** | 0 `privileged: true` / `network_mode: host` / `pid: host` · `user: root` solo en perfil lab — hardened sobrescribe a `redis`/`${API_UID}` (gateado) |
| **Socket crudo** | `netns-guardian` es el **único** actor con `docker.sock` rw — justificado (reparación de sidecars netns requiere DELETE, que el proxy GET/POST no ofrece); allowlist + flow-inventory + gate previo |
| **Contenedores extra** | `soar_test_runner` benigno: `User=app`, 0 caps, no-privileged, `restart:no` — debug ad-hoc documentado |
| **Credenciales default** | Grafana: password generado 32-char + `:?` fail-closed (no `admin/admin`) · ES/MISP/TheHive: todas generadas |
| **Seccomp** | Orborus pierde `seccomp:unconfined` en hardened → perfil default Docker (SOAR-013) |
| **Docs surface** | `API_DOCS_ENABLED=spec` en hardened — solo openapi.json, sin Swagger UI |

## 4. Inventario de residuales aceptados (re-verificado)

Los residuales de las evals 46-63 fueron re-muestreados: **leak `.env*` en GitHub** (aceptado por el usuario, gate anti-nuevos) · snapshots crash-consistent · RPO manual · sin off-site (single-host lab) · egress NAT en `soar_net` (MITM por diseño no, TLS mutuo sí) · ventana self-heal ~45s · fencing por polling · hashes sintéticos en simulador sin advisory · extras dev flotando en imagen (runtime 100% pineado).

**Deuda activa: 0** — todo residual restante es (a) decisión explícita del usuario, (b) restricción física del lab single-host, o (c) compensado por control verificado.

## 5. Gates añadidos (5 nuevos → 15 total)

| Gate | Invariante |
|------|-----------|
| `test_no_eol_nginx_refs_anywhere` | Cero referencias a ramas nginx ≤1.25 en compose + envs |
| `test_edge_image_is_supported_stable` | `NGINX_IMAGE` default ≥ 1.26 en ambos ficheros de edge |
| `test_no_debt_comment_markers_in_src` | Cero `# TODO/FIXME/XXX/HACK` en `src/` — la deuda no puede re-aparecer |
| `test_no_privileged_or_host_modes` | Cero `privileged:`/`network_mode: host`/`pid: host` en todo compose |
| `test_root_users_only_in_lab_profile` | Todo `user: root` de perfil lab tiene override a uid nombrado en hardened |

## 6. Residuales (justificados)

- **`user: root` en perfil lab** (api/redis base): el perfil `up-lab` es explícitamente relajado para depuración; hardened los sobrescribe — gateado.
- **Guardian con socket crudo rw**: excepción allowlist única y documentada; su ausencia reabre el bug de netns stale que existe para cerrar.
- **`test_runner` vivo**: benigno verificado; su recreo es manual (`mk_test_runner.py`).

## 7. Verificación

```
$ pytest tests/architecture/test_residual_hardening.py → 15/15 PASSED
$ edge live: nginx/1.27.5 healthy, HTTPS 200, :80→301
```

## 8. Referencias

- CIS Docker Benchmark §5 — container runtime configuration
- NIST SP 800-53: CM-7 (least functionality), AU-6 (audit review), RA-5 (vuln monitoring)
- ISO/IEC 27001:2022 A.8.8 — management of technical vulnerabilities
- `docs/45-eval-residual-hardening.md` — primera evaluación
- `tests/architecture/test_residual_hardening.py` — 15 gates
