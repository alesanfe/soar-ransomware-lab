# Evaluación multi-marco — Perímetro de red (egress guard + network watcher)

> Evaluación formal del perímetro de red del lab: el sidecar
> `api-egress-guard` (iptables en el netns del api) y el servicio
> `network-watcher` (inspección de conexiones + attach zero-trust de
> workers Shuffle). Metodología de `docs/32`-`38`: hallazgos verificados
> en vivo y pineados con gates
> (`tests/architecture/test_network_perimeter.py`, **12 gates**).
> Revisión 2026-11-11: **1 defecto P0** + 1 menor corregidos.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Seguridad/fiabilidad del perímetro |
| Zero Trust / NIST SP 800-207 | Egress filtering, micro-segmentación, never-trust attach |
| CWE-284 / CWE-693 | Control de acceso al egress, protección incompleta |
| STRIDE | Suplantación de workers, movimiento lateral, exfiltración |
| CIS Docker | NET_ADMIN mínimo, socket via proxy |

## Evidencia de runtime (post-fix)

```
egress guard   netns api == netns guard (net:[4026534737])
               8.8.8.8:443 + 1.1.1.1:80 -> TimeoutError (DROP)
               redis:6379, localhost:8000 -> reachable (interno OK)
self-heal      docker rm+up api -> guard detecta netns muerto (~45s)
               -> exit -> restart -> reattach a netns NUEVO -> healthy
watcher        /health 200, /api/connections 30 conexiones, GET-only
               3 probes connect-close -> 0 tracebacks (fix BrokenPipe)
```

## Hallazgos corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| NET-EVAL-001 | **Egress guard en netns muerto — egress del api ABIERTO con healthcheck verde (P0)** — `network_mode: service:api` se resuelve al arrancar; tras cualquier recreate del api el sidecar seguía durmiendo en el netns viejo con reglas correctas que no protegían nada. El healthcheck E5-03 verificaba la chain **en el netns del sidecar** (persiste para siempre) — exactamente el falso-verde que pretendía evitar. Verificado: netns distintos, `8.8.8.8:443` y `1.1.1.1:80` alcanzables | netns distintos + conectividad externa abierta | Watch loop: `nc -z 127.0.0.1 8000` cada 15s — compartir netns hace que :8000 solo responda mientras el api viva ahí; 3 fallos → `exit 0` → `restart: unless-stopped` re-adjunta al netns nuevo y reinstala reglas. Healthcheck ampliado con co-residencia (nc :8000). Verificado e2e: recreate del api → reattach autónomo → egress DROP |
| NET-EVAL-002 | **`$$` faltante en el comando del guard** — compose interpolaba `$fails`/`$((fails+1))` a vacío → `[ -ge 3 ]` roto (habría impedido el self-heal) | `docker inspect` del Cmd renderizado | `$$fails`/`$$((fails+1))` escapados; renderizado correcto verificado |
| NET-EVAL-003 | `BrokenPipeError` en el watcher — probes que conectan y cierran sin leer (TCP liveness, curls abortados) volcaban traceback a logs | Traceback en logs tras connect-close | `_write_json` tolera `BrokenPipeError`/`ConnectionResetError`; imagen reconstruida; 3 probes → 0 tracebacks |

## Puntos positivos (verificados)

- **Egress whitelist-based**: ACCEPT solo lo/privadas/link-local/conntrack establecido → DROP final; NET_ADMIN en el sidecar mínimo (`netshoot` + nnp + RO + pids=64), nunca en el api.
- **Watcher GET-only**: `/health` + `/api/connections` — cero endpoints mutantes; puerto loopback 15130.
- **Attach zero-trust**: `_verify_trust` (label + image allowlist, modo `hybrid`) **antes** de cualquier `net.connect`/`exec`; name-spoof rechazado por label+imagen (tests existentes).
- **Socket via proxy**: `DOCKER_HOST=tcp://docker-socket-proxy:2375` + `volumes: !reset []` — sin socket crudo en hardened; `WATCHER_DOCKER_SOCKET_INJECT` redirige al proxy también si se reactiva.
- **Healthchecks honestos**: el guard exige chain+salto OUTPUT+co-residencia del api; el watcher verifica la red objetivo existe (503 si no).
- **Input validado**: `limit` acotado 1-1000, `ip` parseado con `ipaddress`.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| Egress guard solo cubre el api | Alcance deliberado: Cortex analyzers (DShield/pDNS), MISP feeds y Orborus (pull de imágenes) requieren internet legítimo — una guardia universal rompería el lab. El api es el único servicio sin egress legítimo. |
| Ventana ~45s de egress abierto tras recreate del api | Acotada por el watch-loop (3×15s); reducible bajando el intervalo a costa de falsos positivos durante restart normal |
| Guard depende del listener :8000 del api | Si el api cambia de puerto hay que actualizar el probe — pineado por gate |
| `inject_hosts` escribe /etc/hosts en workers | Mecanismo de laboratorio documentado; verificación zero-trust previa |

## STRIDE del perímetro

| Amenaza | Control | Estado |
|---|---|---|
| Exfiltración desde el api | EGRESS_GUARD DROP final + self-heal | ✅ |
| Lateral desde workers | Attach solo tras verificación label+imagen | ✅ |
| Spoofing de worker | `WATCHER_TRUST_MODE=hybrid` (nombre+label+imagen) | ✅ |
| Socket abuse | docker-socket-proxy, `!reset []` en hardened | ✅ |
| Evasión por restart | Watch-loop detecta netns muerto y re-adjunta | ✅ |

## Regresión

- **12/12 gates** `test_network_perimeter.py`.
- Vivo: egress DROP verificado tras recreate + self-heal completo; watcher sin tracebacks.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Seguridad del perímetro | 5.0 → **9.5** — el egress estaba ABIERTO |
| Fiabilidad (self-heal) | 6.0 → **9.5** — reattach autónomo |
| Detección de drift | 4.0 → **9.5** — healthcheck co-residencia + watch-loop |
| Mantenibilidad | 8.5 → **9.5** — 12 gates |
| **Global** | ~6.0 → **~9.5** |
