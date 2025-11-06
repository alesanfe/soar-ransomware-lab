
#!/usr/bin/env bash
# Generar TLS autofirmado (placeholder)
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=soar.local"
