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

echo "==> [1/7] Actualizando sistema..."
apt-get update -y
apt-get install -y \
    curl wget git make openssl \
    ca-certificates gnupg lsb-release \
    python3 python3-pip python3-venv \
    net-tools jq

echo "==> [2/7] Instalando Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker "${LAB_USER}"
systemctl enable docker
systemctl start docker

echo "==> [3/7] Clonando/sincronizando repositorio..."
if [ ! -d "${REPO_DIR}/.git" ]; then
    git clone https://github.com/alesanfe/soar-ransomware-lab.git "${REPO_DIR}" || true
fi
# Si no hay git remoto (se usa synced_folder), copia desde /vagrant
if [ ! -d "${REPO_DIR}" ]; then
    cp -r /vagrant "${REPO_DIR}"
fi
chown -R "${LAB_USER}:${LAB_USER}" "${REPO_DIR}"

echo "==> [4/7] Configurando variables de entorno..."
cd "${REPO_DIR}"
if [ ! -f .env.full ]; then
    cp .env.example .env.full 2>/dev/null || cp .env.example .env.full || true
fi

echo "==> [5/7] Generando certificados SSL..."
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

echo "==> [6/7] Levantando stack SOAR con Docker Compose..."
cd "${REPO_DIR}"
# vm.max_map_count para Elasticsearch
sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
# Levantar como vagrant para respetar permisos de docker group
su -c "cd ${REPO_DIR} && make up" "${LAB_USER}" || docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d

echo "==> [7/8] Instalando simulador SIEM Python..."
cd "${REPO_DIR}"
pip3 install -e ".[dev]" 2>/dev/null || pip3 install -r apps/api/requirements.txt || true

echo "==> [8/8] Inicializando webhook de Shuffle en Elasticsearch..."
# Esperar a que Elasticsearch estÃ© listo
ES_URL="http://localhost:9201"
for i in $(seq 1 30); do
    if curl -sf "${ES_URL}/_cluster/health" > /dev/null 2>&1; then
        echo "    Elasticsearch listo"
        break
    fi
    echo "    Esperando Elasticsearch... (${i}/30)"
    sleep 10
done

# Esperar a que Shuffle backend estÃ© listo
SHUFFLE_URL="http://localhost:5001"
for i in $(seq 1 20); do
    if curl -sf "${SHUFFLE_URL}/api/v1/health" > /dev/null 2>&1; then
        echo "    Shuffle backend listo"
        break
    fi
    echo "    Esperando Shuffle... (${i}/20)"
    sleep 10
done

# Registrar el webhook via script Python (que maneja la lÃ³gica completa)
python3 "${REPO_DIR}/scripts/init_shuffle_webhook.py" || echo "    (webhook init diferido - ejecutar manualmente)"

echo ""
echo "============================================================"
echo " SOAR Lab Ubuntu VM lista en https://192.168.56.10"
echo " Web Management : https://192.168.56.10/"
echo " TheHive        : https://192.168.56.10/thehive/"
echo " Cortex         : https://192.168.56.10/cortex/"
echo " Kibana/Wazuh   : https://192.168.56.10/kibana/"
echo " Grafana        : https://192.168.56.10/grafana/"
echo " Shuffle        : https://192.168.56.10:3001/"
echo "============================================================"
