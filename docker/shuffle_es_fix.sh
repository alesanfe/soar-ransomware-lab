#!/usr/bin/env bash
# Semilla para arreglar el índice 'environments' de Shuffle en Elasticsearch
# Ejecuta desde el host. Requiere curl y acceso al puerto 19200 (mapeado a 9200 del contenedor).
set -euo pipefail
ES="http://localhost:19200"

echo "Borrando índice environments si existe..."
curl -s -o /dev/null -w '
HTTP %{http_code}
' -XDELETE "$ES/environments" || true

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ORG_ID="00000000-0000-0000-0000-000000000000"
ENV_ID="11111111-1111-1111-1111-111111111111"

cat > /tmp/env_doc.json <<JSON
{
  "Name": "Shuffle",
  "Type": "onprem",
  "Registered": false,
  "default": true,
  "archived": false,
  "id": "${ENV_ID}",
  "org_id": "${ORG_ID}",
  "created": "${TS}"
}
JSON

echo "Creando documento inicial con campo 'created' para generar el mapeo..."
curl -s -o /dev/null -w '
HTTP %{http_code}
' -XPOST "$ES/environments/_doc" -H 'Content-Type: application/json' --data-binary @/tmp/env_doc.json

echo "Verificando el índice environments..."
curl -s "$ES/environments/_search?size=1&pretty=true"
