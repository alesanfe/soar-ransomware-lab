#!/usr/bin/env bash
# ==============================================================================
# SOAR Ransomware Lab - Ubuntu VM Provisioning
# Instala Docker, Compose, el stack SOAR completo y el simulador SIEM
# ==============================================================================
# Guard: re-exec stripping CRLF if needed (safe when run from Windows host)
if file "$0" 2>/dev/null | grep -q CRLF; then
  sed 's/\r//' "$0" > /tmp/_provision_lf.sh
  exec bash /tmp/_provision_lf.sh "$@"
fi
set -euo pipefail

REPO_DIR="/opt/soar-ransomware-lab"
LAB_USER="vagrant"

echo "==> [1/8] Actualizando sistema..."
apt-get update -y
apt-get install -y \
    curl wget git make openssl \
    ca-certificates gnupg lsb-release \
    python3 python3-pip python3-venv \
    net-tools jq

echo "==> [2/8] Instalando Docker..."
install -m 0755 -d /etc/apt/keyrings
rm -f /etc/apt/keyrings/docker.gpg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker "${LAB_USER}"
systemctl enable docker
systemctl start docker

echo "==> [3/8] Clonando/sincronizando repositorio..."
# Con synced_folder el repo ya está en REPO_DIR — no hace falta clonar
if [ ! -d "${REPO_DIR}" ]; then
    git clone https://github.com/alesanfe/soar-ransomware-lab.git "${REPO_DIR}" || true
fi
chown -R "${LAB_USER}:${LAB_USER}" "${REPO_DIR}" 2>/dev/null || true

echo "==> [4/8] Configurando variables de entorno..."
cd "${REPO_DIR}"
if [ ! -f .env.full ]; then
    cp .env.example .env.full 2>/dev/null || true
fi

# En Vagrant los datos pesados van a un directorio local (ext4) para evitar la
# lentitud de VirtualBox shared folders. Los logs y resultados se comparten con
# el host a través del synced folder mediante bind mounts.
LOCAL_ARTIFACTS_DIR="/var/lib/soar/artifacts"
mkdir -p "${LOCAL_ARTIFACTS_DIR}"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/elasticsearch" "${LOCAL_ARTIFACTS_DIR}/data/thehive/files" "${LOCAL_ARTIFACTS_DIR}/data/cortex"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/shuffle/apps" "${LOCAL_ARTIFACTS_DIR}/data/shuffle/files"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/redis" "${LOCAL_ARTIFACTS_DIR}/data/misp/db" "${LOCAL_ARTIFACTS_DIR}/data/misp/files"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/misp/configs" "${LOCAL_ARTIFACTS_DIR}/data/misp/logs"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/wazuh/config" "${LOCAL_ARTIFACTS_DIR}/data/wazuh/api_config" "${LOCAL_ARTIFACTS_DIR}/data/wazuh/etc"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/wazuh/queue" "${LOCAL_ARTIFACTS_DIR}/data/wazuh/var_multigroups"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/wazuh/integration_files" "${LOCAL_ARTIFACTS_DIR}/data/wazuh/active_response"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/wazuh/wodles" "${LOCAL_ARTIFACTS_DIR}/data/wazuh/logs"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/data/kibana" "${LOCAL_ARTIFACTS_DIR}/data/loki" "${LOCAL_ARTIFACTS_DIR}/data/grafana"
mkdir -p "${LOCAL_ARTIFACTS_DIR}/backups" "${LOCAL_ARTIFACTS_DIR}/results" "${LOCAL_ARTIFACTS_DIR}/coverage"
mkdir -p "${REPO_DIR}/artifacts/logs" "${REPO_DIR}/artifacts/results"
# Compartir logs y results con el host via mount --bind
mountpoint -q "${LOCAL_ARTIFACTS_DIR}/logs" && umount "${LOCAL_ARTIFACTS_DIR}/logs"
mountpoint -q "${LOCAL_ARTIFACTS_DIR}/results" && umount "${LOCAL_ARTIFACTS_DIR}/results"
mount --bind "${REPO_DIR}/artifacts/logs" "${LOCAL_ARTIFACTS_DIR}/logs"
mount --bind "${REPO_DIR}/artifacts/results" "${LOCAL_ARTIFACTS_DIR}/results"
# Hacer los bind mounts persistentes tras reinicios
if ! grep -q "${LOCAL_ARTIFACTS_DIR}/logs" /etc/fstab; then
    echo "${REPO_DIR}/artifacts/logs ${LOCAL_ARTIFACTS_DIR}/logs none bind 0 0" >> /etc/fstab
    echo "${REPO_DIR}/artifacts/results ${LOCAL_ARTIFACTS_DIR}/results none bind 0 0" >> /etc/fstab
fi

# Establecer ARTIFACTS_DIR para que los binds de Docker apunten al directorio local
if ! grep -q "^ARTIFACTS_DIR=" .env.full; then
    echo "ARTIFACTS_DIR=${LOCAL_ARTIFACTS_DIR}" >> .env.full
else
    sed -i "s|^ARTIFACTS_DIR=.*|ARTIFACTS_DIR=${LOCAL_ARTIFACTS_DIR}|" .env.full
fi

echo "==> [5/8] Generando certificados SSL..."
SSL_DIR="${REPO_DIR}/infra/docker/nginx/ssl"
mkdir -p "${SSL_DIR}"
if [ ! -f "${SSL_DIR}/soar.local.crt" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${SSL_DIR}/soar.local.key" \
        -out "${SSL_DIR}/soar.local.crt" \
        -subj "/C=ES/ST=Madrid/L=Madrid/O=SOAR-Lab/CN=soar.local" \
        -addext "subjectAltName=IP:192.168.56.10,DNS:soar.local,DNS:localhost"
    echo "    Certificados generados en ${SSL_DIR}"
fi

echo "==> [5b/8] Configurando swap (4GB) para evitar OOM durante descarga de imágenes..."
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "    Swap de 4GB activado"
fi

echo "==> [6/8] Levantando stack SOAR con Docker Compose..."
cd "${REPO_DIR}"
# vm.max_map_count para Elasticsearch
sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" >> /etc/sysctl.conf

# Crear directorios necesarios
mkdir -p artifacts/data/elasticsearch artifacts/data/thehive/files artifacts/data/cortex
mkdir -p artifacts/data/shuffle/apps artifacts/data/shuffle/files
mkdir -p artifacts/data/redis artifacts/data/misp/db artifacts/data/misp/files
mkdir -p artifacts/data/misp/configs artifacts/data/misp/logs
mkdir -p artifacts/data/wazuh/config artifacts/data/wazuh/api_config artifacts/data/wazuh/etc
mkdir -p artifacts/data/wazuh/queue artifacts/data/wazuh/var_multigroups
mkdir -p artifacts/data/wazuh/integration_files artifacts/data/wazuh/active_response
mkdir -p artifacts/data/wazuh/wodles artifacts/data/wazuh/logs
mkdir -p artifacts/data/kibana artifacts/data/loki artifacts/data/grafana
mkdir -p artifacts/backups artifacts/logs artifacts/results artifacts/coverage

# Pre-pull imágenes con timeouts frecuentes (reintentar individualmente)
for img in "tenzir/tenzir:main" \
           "ghcr.io/shuffle/shuffle-backend:2.2.1" \
           "ghcr.io/shuffle/shuffle-frontend:2.2.1" \
           "thehiveproject/thehive:latest" \
           "ghcr.io/misp/misp-docker/misp-core:latest" \
           "wazuh/wazuh-manager:4.14.0" \
           "wazuh/wazuh-indexer:4.14.0" \
           "wazuh/wazuh-dashboard:4.14.0"; do
    for attempt in 1 2 3 4 5; do
        docker pull "$img" && break || {
            echo "    Pull de $img intento $attempt fallido, reintentando en 20s..."
            sleep 20
        }
    done
done

# Levantar el stack sin logging (opcional, reduce carga de red en Vagrant)
# El override de Vagrant usa volúmenes Docker nativos en lugar de bind mounts
# para evitar problemas de bloqueo de VirtualBox shared folders.
_DC_CMD="docker compose -p soar \
    -f infra/docker/compose/docker-compose.yml \
    -f infra/docker/compose/docker-compose.core.yml \
    -f infra/docker/compose/docker-compose.misp.yml \
    -f infra/docker/compose/docker-compose.wazuh.yml \
    -f infra/docker/compose/docker-compose.api.yml \
    -f infra/docker/compose/docker-compose.vagrant.yml \
    --env-file .env.full"

# Limpiar volúmenes de provisiones anteriores para evitar datos corruptos
echo "    Limpiando volúmenes Docker anteriores..."
${_DC_CMD} down -v 2>/dev/null || true
# Limpiar específicamente volumen Redis (problema AOF en Vagrant)
docker volume rm -f soar_redis_data 2>/dev/null || true
docker volume rm -f ${COMPOSE_PROJECT_NAME:-soar}_redis_data 2>/dev/null || true
for attempt in 1 2 3 4 5; do
    echo "    Intento ${attempt}/5 de docker compose up..."
    ${_DC_CMD} up -d --build && break || {
        echo "    Intento ${attempt} fallido, reintentando en 30s..."
        sleep 30
    }
done

echo "==> [6b/8] Inicializando Cortex y TheHive..."
for i in $(seq 1 30); do
    if docker exec soar_elasticsearch wget -qO- "http://localhost:9200/_cluster/health" > /dev/null 2>&1; then
        echo "    Elasticsearch listo"
        break
    fi
    echo "    Esperando Elasticsearch... (${i}/30)"
    sleep 10
done
docker exec soar_api python /app/src/soar_lab/infrastructure/setup/reset_cortex.py || true

echo "==> [7/9] Instalando simulador SIEM Python..."
cd "${REPO_DIR}"
pip3 install -e ".[dev]" 2>/dev/null || pip3 install -r apps/api/requirements.txt || true

echo "==> [8/9] Inicializando webhook de Shuffle..."
# Esperar a que Shuffle backend esté listo (healthcheck del contenedor)
for i in $(seq 1 60); do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' soar_shuffle_backend 2>/dev/null)" = "healthy" ]; then
        echo "    Shuffle backend listo"
        break
    fi
    echo "    Esperando Shuffle... (${i}/60)"
    sleep 5
done
sleep 10  # Esperar inicialización completa

# Registrar el webhook via script Python desde dentro del contenedor
docker exec soar_api python /app/src/soar_lab/infrastructure/setup/init_shuffle_webhook.py || echo "    (webhook init diferido - ejecutar manualmente)"

echo ""
echo "==> [8b/9] Conectando soar_api a logging_net (para Grafana)..."
docker network connect logging_net soar_api 2>/dev/null || echo "    (ya conectado o red no existe)"

echo "==> [8c/9] Copiando .env.full al contenedor soar_api..."
docker cp "${REPO_DIR}/.env.full" soar_api:/app/.env.full || echo "    (advertencia: no se pudo copiar .env.full)"

echo "==> [8d/9] Limpiando workers Wazuh cacheados (imagen obsoleta)..."
docker ps -a --format "{{.Names}}" | grep "Wazuh_1-1-0" | xargs -r docker rm -f 2>/dev/null || true

echo "==> [9/9] Ejecutando suite E2E completo..."
cd "${REPO_DIR}"
docker exec soar_api python -m pytest tests/e2e/ --tb=line -v 2>&1 | tee /tmp/e2e_results.log || echo "    Suite E2E completado (ver /tmp/e2e_results.log)"
echo "    Resultados guardados en /tmp/e2e_results.log"

echo ""
echo "============================================================"
echo " SOAR Lab Ubuntu VM lista en https://192.168.56.10"
echo " Web Management : https://localhost:8443/"
echo " TheHive        : https://localhost:8443/thehive/"
echo " Cortex         : https://localhost:8443/cortex/"
echo " Kibana/Wazuh   : https://localhost:8443/kibana/"
echo " Grafana        : https://localhost:8443/grafana/ (Dashboard KPIs disponible)"
echo " Shuffle        : https://localhost:8081/"
echo ""
echo " Para ver los KPIs en Grafana:"
echo "   1. Abre https://localhost:8443/grafana/"
echo "   2. Dashboard: 'SOAR Ransomware Lab - KPIs Dashboard'"
echo ""
echo " Resultados de tests E2E:"
echo "   Suite completo: cat /tmp/e2e_results.log"
echo "============================================================"
