# Runbook — Analyst-in-the-loop para containment (F4)

Con `SOAR_CONTAIN_REQUIRE_APPROVAL=1`, `POST /api/v1/contain` no actúa:
aparca la petición y devuelve `status=pending_approval` + `approval_id`.
Un analista humano aprueba o rechaza — el gap de tiempo es el MTTR
humano medible frente al automatizado.

## Flujo

1. **Listar pendientes**:
   `GET /api/v1/contain/approvals` (auth requerida) → tickets con la
   petición original (alert_id, case_id, hostname, mode).
2. **Aprobar**:
   `POST /api/v1/contain/{approval_id}/approve?decided_by=analyst`
   → ejecuta la petición registrada (simulated o enforce) y devuelve
   el `ContainmentResponse` normal.
3. **Rechazar**:
   `POST /api/v1/contain/{approval_id}/reject?decided_by=analyst`.

## Semántica

- Los tickets caducan a los `3600s` (default) → `expired`, sin efecto.
- Backlog acotado a 500 pendientes — un workflow en bucle no agota
  memoria (`429` cuando está lleno).
- Aprobar/rechazar dos veces → `404` (decisión única, no idempotente
  por diseño: una decisión humana no se reemplaza en silencio).
- Con `SOAR_CONTAIN_REQUIRE_APPROVAL` off (default) el endpoint actúa
  directamente — comportamiento previo intacto.

## Verificación

`tests/unit/application/test_containment_approval.py` (7 tests).
