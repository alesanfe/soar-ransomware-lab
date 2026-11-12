# Evaluación Victim Simulator — MITRE ATT&CK / CALDERA / Atomic Red Team

> **Fecha**: 2026-11-12 · **Suite**: `tests/architecture/test_victim_stack.py` (17 gates) · **Resultado**: defecto crítico de realismo corregido + kill-chain ampliada.

## 1. Defectos encontrados y corregidos

| ID | Severidad | Defecto | Fix | Evidencia |
|----|-----------|---------|-----|-----------|
| VICTIM-EVAL-006 | **Crítica** | **La telemetría `[atomic:*]` nunca llegaba a Loki** — `docker exec` escribe en la TTY del exec, no en el stdout del contenedor; `victim_sim` tenía **0 streams** en Loki (PID1 `sleep` no logea). La promesa del docstring era falsa. | Telemetría redirigida a `/proc/1/fd/1` (stdout de PID 1 → json-file driver → Promtail) | Perfil completo ejecutado → **10 líneas `[atomic:*]` verificadas en Loki** (antes: 0) |
| VICTIM-EVAL-007 | Alta | **Cobertura TTP insuficiente**: solo 4 técnicas / 3 tácticas (execution, credential-access, impact) — sin discovery, persistencia, def.-evasion, collection, C2 | 4 → **10 técnicas** cubriendo **8 tácticas** del kill-chain ransomware | gate `test_all_ransomware_tactics_covered` |
| VICTIM-EVAL-008 | Media | Sin perfil de adversario ni cleanup (artefactos persistían; runs no idempotentes) | `PROFILES["ransomware"]` ordenado discovery→impact + `cleanup` por técnica | `--list`, `-p ransomware`, `--no-cleanup` |

## 2. Matriz por dimensión

| Dimensión | Marco | Estado |
|-----------|-------|--------|
| **Cobertura TTPs** | MITRE ATT&CK | 10 técnicas / 8 tácticas: T1059, T1082, T1083, T1053, T1070, T1003, T1005, T1560, T1071, T1490, T1486 — kill-chain ransomware completo |
| **Realismo** | Atomic Red Team | Comandos bounded no-destructivos que simulan comportamiento observable (archivos, procesos, tampering) — honesto: harness, no ART real |
| **Repetibilidad** | CALDERA abilities | Comandos deterministas + `cleanup` por técnica → runs idempotentes; `--profile` reproduce el kill-chain completo |
| **Aislamiento** | — | nobody uid, cap_drop ALL, read_only, tmpfs exec, pids:32, soar.victim label → target legítimo de containment drills (diseño) |
| **Telemetría válida** | — | `/proc/1/fd/1` → json-file → Promtail → **Loki verificado E2E**; tagged `[atomic:tid]` para correlación con detecciones |

## 3. Residuales (diseño honesto)

| Restricción | Naturaleza |
|-------------|------------|
| Simulación sin payloads destructivos | Decisión deliberada: bounded/non-destructive — un ART real exigiría Windows+Sysmon, fuera del scope de un lab containerizado |
| Técnicas sin parsers de output | La detección es por tag + contenido (suficiente para el pipeline del lab) |
