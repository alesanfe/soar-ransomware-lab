#!/bin/bash
# Verificar estado de Shuffle
sudo docker exec soar_api curl -s -X POST http://soar_shuffle_backend:5001/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"R3x#7mP9$vK4@nQ2tW8!zY5&hF1sD3"}'
