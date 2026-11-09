# ADR-0007: Fail-open para limiters, fail-closed para auth

**Estado**: Aceptado

## Contexto

Dos controles de middleware con semánticas de fallo opuestas; mezclarlas
produce o DoS auto-infligido (limiter fail-closed) o bypass de seguridad
(auth fail-open).

## Decisión

- **Auth (`DefaultDenyAuthMiddleware`)**: **fail-closed**. Cualquier ruta
  no whitelisted sin credencial válida → 401; un rol no clasificado → el
  tier más restrictivo aplicable. Un error interno de auth no concede
  acceso.
- **Rate limiter**: **fail-open**. Si el backend (Redis/memoria) lanza,
  la request pasa y se loguea warning ≤1/minuto — un limitador es
  protección de disponibilidad, no un gate de seguridad; que Redis muera
  no debe tumbar la API.
- **Startup validation**: **fail-warn** (`Settings.validate` loguea, no
  aborta) — el lab corre parcialmente sin algunas integraciones.
- **TLS verify**: **fail-closed** por defecto (ADR-0005); el apagado es
  opt-in explícito y auditado.

## Consecuencias

- Regla memorable: *la seguridad falla cerrada, la protección de
  disponibilidad falla abierta*.
- Riesgo aceptado: un Redis caído deja sin throttling compartido
  (fail-open) — mitigado por el warning rate-limited y la alerta en logs.
