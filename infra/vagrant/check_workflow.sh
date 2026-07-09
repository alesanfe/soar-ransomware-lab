#!/bin/bash
# Verificar el estado del workflow en Shuffle
curl -s -H "Authorization: Bearer e18f1fe3-1591-44ec-aff4-c6e759b3a8bf" \
  http://soar_shuffle_backend:5001/api/v1/workflows/162eae78-69fa-472d-a61f-4b9496f96e55
