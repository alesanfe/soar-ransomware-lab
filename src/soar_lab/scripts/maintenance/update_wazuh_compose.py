import pathlib

WAZUH_COMPOSE = pathlib.Path('infra/docker/wazuh/docker-compose.yml')
WAZUH_COMPOSE.write_text('''# Wazuh 4.14 single-node stack on OpenSearch 2.10.0
# Certificates must be generated first:
#   docker compose -f infra/docker/wazuh/generate-indexer-certs.yml run --rm generator
# Then start only Wazuh:
#   docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.wazuh.yml up -d

services:
  wazuh.manager:
    image: wazuh/wazuh-manager:4.14.0
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_wazuh_manager
    hostname: wazuh.manager
    restart: unless-stopped
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 655360
        hard: 655360
    ports:
      - "${WAZUH_EVENTS_PORT:-15141}:1514"
      - "${WAZUH_ENROLLMENT_PORT:-1515}:1515"
      - "${WAZUH_SYSLOG_PORT:-514}:514/udp"
      - "${WAZUH_API_PORT:-55100}:55000"
    environment:
      - INDEXER_URL=https://wazuh.indexer:9200
      - INDEXER_USERNAME=${WAZUH_INDEXER_USERNAME:-admin}
      - INDEXER_PASSWORD=${WAZUH_INDEXER_PASSWORD}
      - FILEBEAT_SSL_VERIFICATION_MODE=full
      - SSL_CERTIFICATE_AUTHORITIES=/etc/ssl/root-ca.pem
      - SSL_CERTIFICATE=/etc/ssl/filebeat.pem
      - SSL_KEY=/etc/ssl/filebeat.key
      - API_USERNAME=${WAZUH_API_USERNAME:-wazuh-wui}
      - API_PASSWORD=${WAZUH_API_PASSWORD}
    volumes:
      - wazuh_api_configuration:/var/ossec/api/configuration
      - wazuh_etc:/var/ossec/etc
      - wazuh_logs:/var/ossec/logs
      - wazuh_queue:/var/ossec/queue
      - wazuh_var_multigroups:/var/ossec/var/multigroups
      - wazuh_integrations:/var/ossec/integrations
      - wazuh_active_response:/var/ossec/active-response/bin
      - wazuh_agentless:/var/ossec/agentless
      - wazuh_wodles:/var/ossec/wodles
      - filebeat_etc:/etc/filebeat
      - filebeat_var:/var/lib/filebeat
      - ./config/wazuh_indexer_ssl_certs/root-ca-manager.pem:/etc/ssl/root-ca.pem
      - ./config/wazuh_indexer_ssl_certs/wazuh.manager.pem:/etc/ssl/filebeat.pem
      - ./config/wazuh_indexer_ssl_certs/wazuh.manager-key.pem:/etc/ssl/filebeat.key
      - ./config/wazuh_cluster/wazuh_manager.conf:/wazuh-config-mount/etc/ossec.conf
    networks:
      - soar_net
    depends_on:
      wazuh.indexer:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "/var/ossec/bin/wazuh-control status || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  wazuh.indexer:
    image: wazuh/wazuh-indexer:4.14.0
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_wazuh_indexer
    hostname: wazuh.indexer
    restart: unless-stopped
    ports:
      - "${WAZUH_INDEXER_PORT:-9200}:9200"
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${WAZUH_INDEXER_PASSWORD}
      - bootstrap.memory_lock=true
      - network.host=0.0.0.0
      - node.name=wazuh.indexer
      - cluster.name=wazuh-cluster
      - cluster.initial_cluster_manager_nodes=wazuh.indexer
      - node.max_local_storage_nodes=1
      - plugins.security.allow_default_init_securityindex=true
      - compatibility.override_main_response_version=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - wazuh-indexer-data:/var/lib/wazuh-indexer
      - ./config/wazuh_indexer_ssl_certs/root-ca.pem:/usr/share/wazuh-indexer/config/certs/root-ca.pem
      - ./config/wazuh_indexer_ssl_certs/wazuh.indexer-key.pem:/usr/share/wazuh-indexer/config/certs/wazuh.indexer.key
      - ./config/wazuh_indexer_ssl_certs/wazuh.indexer.pem:/usr/share/wazuh-indexer/config/certs/wazuh.indexer.pem
      - ./config/wazuh_indexer_ssl_certs/admin.pem:/usr/share/wazuh-indexer/config/certs/admin.pem
      - ./config/wazuh_indexer_ssl_certs/admin-key.pem:/usr/share/wazuh-indexer/config/certs/admin-key.pem
      - ./config/wazuh_indexer/wazuh.indexer.yml:/usr/share/wazuh-indexer/config/opensearch.yml
      - ./config/wazuh_indexer/internal_users.yml:/usr/share/wazuh-indexer/config/opensearch-security/internal_users.yml
    networks:
      - soar_net
    healthcheck:
      test: ["CMD-SHELL", "curl -fsSk https://localhost:9200/_cluster/health -u ${WAZUH_INDEXER_USERNAME:-admin}:${WAZUH_INDEXER_PASSWORD} | grep -q 'green\\|yellow' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:4.14.0
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_wazuh_dashboard
    hostname: wazuh.dashboard
    restart: unless-stopped
    ports:
      - "${WAZUH_DASHBOARD_PORT:-15601}:5601"
    environment:
      - INDEXER_USERNAME=${WAZUH_INDEXER_USERNAME:-admin}
      - INDEXER_PASSWORD=${WAZUH_INDEXER_PASSWORD}
      - WAZUH_API_URL=https://wazuh.manager
      - DASHBOARD_USERNAME=${WAZUH_DASHBOARD_USERNAME:-kibanaserver}
      - DASHBOARD_PASSWORD=${WAZUH_DASHBOARD_PASSWORD}
      - API_USERNAME=${WAZUH_API_USERNAME:-wazuh-wui}
      - API_PASSWORD=${WAZUH_API_PASSWORD}
    volumes:
      - ./config/wazuh_indexer_ssl_certs/wazuh.dashboard.pem:/usr/share/wazuh-dashboard/certs/wazuh-dashboard.pem
      - ./config/wazuh_indexer_ssl_certs/wazuh.dashboard-key.pem:/usr/share/wazuh-dashboard/certs/wazuh-dashboard-key.pem
      - ./config/wazuh_indexer_ssl_certs/root-ca.pem:/usr/share/wazuh-dashboard/certs/root-ca.pem
      - ./config/wazuh_dashboard/opensearch_dashboards.yml:/usr/share/wazuh-dashboard/config/opensearch_dashboards.yml
      - ./config/wazuh_dashboard/wazuh.yml:/usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml
      - wazuh-dashboard-config:/usr/share/wazuh-dashboard/data/wazuh/config
      - wazuh-dashboard-custom:/usr/share/wazuh-dashboard/plugins/wazuh/public/assets/custom
    networks:
      - soar_net
    depends_on:
      wazuh.indexer:
        condition: service_healthy
      wazuh.manager:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -fsSk https://localhost:5601/login || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  soar_net:
    name: soar_net
    driver: bridge

volumes:
  wazuh_api_configuration:
  wazuh_etc:
  wazuh_logs:
  wazuh_queue:
  wazuh_var_multigroups:
  wazuh_integrations:
  wazuh_active_response:
  wazuh_agentless:
  wazuh_wodles:
  filebeat_etc:
  filebeat_var:
  wazuh-indexer-data:
  wazuh-dashboard-config:
  wazuh-dashboard-custom:
''')

PROJECT_WAZUH = pathlib.Path('infra/docker/compose/docker-compose.wazuh.yml')
PROJECT_WAZUH.write_text('''# === Wazuh 4.14 SIEM stack (Indexer + Dashboard + Manager) ===
# Requires certificates generated in infra/docker/wazuh/:
#   docker compose -f infra/docker/wazuh/generate-indexer-certs.yml run --rm generator

include:
  - path: ../wazuh/docker-compose.yml

# This file intentionally left minimal; all Wazuh services are defined in infra/docker/wazuh/docker-compose.yml
''')

print('Wazuh compose files updated')
