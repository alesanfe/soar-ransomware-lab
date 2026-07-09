#!/bin/bash
# Verificar API key de Shuffle
sudo docker exec soar_api curl -s -H "Authorization: Bearer f2a8b3c9-d4e1-5f6a-7b8c-9d0e1f2a3b4c" \
  http://soar_shuffle_backend:5001/api/v1/workflows 2>&1 | head -20
