# Evaluación Backup/DR — ISO 22301 / ISO 27031 / NIST SP 800-34

> **Fecha**: 2026-11-12 · **Resultado**: **2 defectos corregidos** (archivos en claro + pipeline sin ejercicio periódico). Score ~9,5/10.

## Defectos corregidos

| ID | Defecto | Fix | Evidencia live |
|----|---------|-----|----------------|
| DR-EVAL-006 | **Archivos de backup en claro** — `tar.gz` sin cifrar en `runtime/backups/` llevando `grafana.db`, configs MISP, volúmenes TheHive/Redis (datos credencial-adyacentes) | AES-256-CBC + PBKDF2 600k vía openssl sobre cada tarball; `BACKUP_PASSPHRASE` obligatorio (fail-closed; resuelto desde env exportado o `.env.full`/`.env`); hash SHA-256 del artefacto cifrado; drill descifra a `mktemp` scratch — el set permanece cifrado | Backup sintético: `195B, 5 members → .tar.gz.enc` → drill `sha256 verified → 2 files, 2 markers` · passphrase incorrecta → `bad decrypt` · sin passphrase ni env files → `FAIL … refusing plaintext-backup workflow` exit 1 |
| DR-EVAL-007 | **Pipeline sin ejercicio periódico** — el job CI `backup-test` solo importaba la clase | `BACKUP_VOLUMES` override + job `dr-drill` en ci.yml: crea volumen sintético, siembra ficheros, ejecuta backup→drill E2E en cada pipeline | Gate `test_ci_exercises_drill_pipeline` |

## Matriz por dimensión

| Dimensión | Marco | Estado verificado |
|-----------|-------|-------------------|
| **RPO/RTO** | ISO 22301 §8.4 / NIST 800-34 §3 | **RTO medido**: obs ~94s (doc-24), drill sintético 6s; **RPO** = cadencia del backup (manual — `make backup-obs`/`backup-core`; documentado como decisión lab, recomendado semanal y pre-`reset` que ya preserva credenciales + `.env.full`) |
| **Restauración real** | NIST 800-34 CP-4 / ISO 27031 §5.3 | Drill restaura a volúmenes `*_drill` scratch — nunca toca datos vivos; verifica count archivo↔restaurado + markers de contenido (no solo "el tar se abre") |
| **Cifrado** | ISO 27031 / A.8.13 | ✅ NUEVO (DR-EVAL-006): AES-256-CBC/PBKDF2-600k, fail-closed, wrong-key detectado (`bad decrypt`) |
| **Pruebas periódicas** | ISO 22301 §8.5 / NIST 800-34 §5 | ✅ NUEVO (DR-EVAL-007): pipeline completo ejercido en CI por pipeline; manual: `make drill-obs`/`drill-core` |
| **Integridad** | ISO 27031 §5.4 | SHA256SUMS por artefacto (sobre el `.enc` almacenado) + `gzip -t` + miembros>0 + MANIFEST con digests de imagen + sidecar `.sha256` en el driver API |
| **Resiliencia** | NIST 800-34 §3.4 | Retención `BACKUP_KEEP=5` (prune), fail-closed en cada paso, cobertura de volúmenes **gateada** (todo volumen declarado debe estar cubierto o exento), host-binds incluidos (`api_data`), tenzir anon vols resueltos live |

## Detalles de implementación

- `openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt` — PBKDF2 iter 600k (recomendación OWASP para PBKDF2-HMAC-SHA256)
- `SHA256SUMS` ahora registra `<hash>  <name>.tar.gz.enc` → drill verifica con `sha256sum -c` directo
- Passphrase resuelve: env exportado → `.env.full` → `.env`; strip CRLF; `export` requerido porque `openssl -pass env:` lee el env del proceso (bug detectado y corregido durante la verificación)
- Legacy: los sets de backup previos quedaron en claro en `runtime/backups/` — artefactos locales gitignored, gestionables con `rm` o re-backup; los nuevos nacen cifrados

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Crash-consistent snapshots | Volúmenes tar'eados en caliente — decisión lab documentada (producción exigiría quiesce/snapshot) |
| RPO manual | Sin scheduler — apropiado para lab; la cadencia recomendada está documentada |
| Off-site | Backups en `runtime/backups/` local — lab single-host (S3 backend existe para extensión futura) |
| API codebase archive sin cifrar | Excluye secretos por diseño (gateado); contiene solo código+config pública |

## Regresión

`test_backup_dr.py`: 13 → **30 gates** · regresión arquitectura completa verificada tras los cambios.
