# apps/api/docs

Este directorio contenía documentación HTML estática generada manualmente con puertos, URLs y credenciales obsoletas. Los archivos originales se han movido a `legacy/` para conservar el historial sin exponerlos como referencia operativa.

La documentación vigente del API se encuentra en:

- `docs/API_DOCUMENTATION.md`
- `docs/integrations/api_contracts.md`
- `docs/api/openapi.json` (fuente de verdad)
- Swagger UI accesible desde el contenedor `soar_api` (`/docs` interno) o a través del puerto directo documentado.

> **Nota:** no utilizar los archivos HTML de `legacy/` como fuente de verdad; contienen referencias a `localhost:8000`, `localhost:15601`, `Wazuh Dashboard (Kibana)` y credenciales de ejemplo que ya no son válidas.
