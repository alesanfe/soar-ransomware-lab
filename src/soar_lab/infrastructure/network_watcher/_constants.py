"""Constants for the network watcher.

Constants inlined to avoid installing the full soar_lab package in the
lightweight Alpine container. Keep in sync with soar_lab.common.constants.
"""

import os

CONTENT_TYPE_JSON = "application/json"
HEADER_CONTENT_TYPE = "Content-Type"
DEFAULT_DOCKER_SOCKET_MODE = 777

TARGET_NETWORK = os.environ.get("TARGET_NETWORK", "soar_net")
