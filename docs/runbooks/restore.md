# Runbook — Backup → restore verificado (OP3)

## Crear

`make backup` → `soar_backup_<ts>.tar.gz` + sidecar `.sha256` en
`BACKUP_DIR` (driver `TarBackupDriver`, verificado al escribirse).

## Validar sin restaurar (dry-run)

El endpoint `validate` corre `tar -tzf` + checksum sin tocar el árbol
vivo — usar antes de cualquier restore real.

## Restaurar

`make restore` → verifica integridad (sidecar sha256 + tar listing)
**antes** de extraer: un archivo corrupto nunca clobbers live files.
Los bind-mounts read-only se saltan automáticamente.

## Retención

`BackupService.apply_retention(keep=N)` — count-based; los `.sha256`
se borran con su archivo.

## Evidencia automática

`tests/unit/application/test_backup_restore_roundtrip.py` hace el
round-trip real en tmp dirs (crear → corromper → restaurar → bytes
idénticos) y verifica que un tarball manipulado se rechaza por sha256.
