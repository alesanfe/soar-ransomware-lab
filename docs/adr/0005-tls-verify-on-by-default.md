# ADR-0005: Verificación TLS ON por defecto

**Estado**: Aceptado · **Evidencia**: BUG-110

## Contexto

`verify=False` estaba hardcodeado en el alert sender y como dict inline
en el composition root — un comportamiento inseguro por defecto, invisible
para el operador.

## Decisión

Cero `False` hardcodeado en producción: cada integración lee
`<SERVICIO>_VERIFY_TLS` (`AIOHTTP`, `THEHIVE`, `CORTEX`, `SHUFFLE`,
`ALERT_SENDER`, `MISP`, `GRAFANA`, `ELASTICSEARCH`), default `true`.
Desactivar exige una env var explícita y emite un warning en logs. Las
URLs `http://` internas del lab no se ven afectadas (no hay TLS que
verificar); solo aplica a `https://`.

## Consecuencias

- Postura segura por omisión; el lab sigue funcionando sobre HTTP interno.
- Si un endpoint futuro usa HTTPS autofirmado, requiere la env var
  explícita — el apagado queda auditado en config, no escondido en código.
