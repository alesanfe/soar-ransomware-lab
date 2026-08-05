#!/bin/bash
set -e

cat > /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml <<EOF
hosts:
  - 1513629884013:
      url: "${WAZUH_API_URL:-https://wazuh.manager}"
      port: ${API_PORT:-55000}
      username: "${API_USERNAME:-wazuh-wui}"
      password: "${API_PASSWORD:-wazuh-wui}"
      run_as: ${RUN_AS:-false}
EOF

exec /entrypoint.sh
