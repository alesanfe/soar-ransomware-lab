"""Shared constants for the SOAR Ransomware Lab.

Centralizes values that were previously duplicated as module-level
constants or magic literals across multiple files (e.g.
``METRICS_INDEX``, ``SERVICE_THEHIVE``).
"""

__all__ = [
    # Index names
    "METRICS_INDEX",
    "ALERTS_INDEX",
    "SHUFFLE_EXECUTION_INDEX",
    # Service names
    "SERVICE_THEHIVE",
    "SERVICE_CORTEX",
    "SERVICE_MISP",
    "SERVICE_SHUFFLE",
    "SERVICE_ELASTICSEARCH",
    # HTTP headers and content types
    "HEADER_CONTENT_TYPE",
    "HEADER_ACCEPT",
    "HEADER_AUTHORIZATION",
    "CONTENT_TYPE_JSON",
    "CONTENT_TYPE_NDJSON",
    "AUTH_BEARER_PREFIX",
    "AUTH_BASIC_PREFIX",
    # JWT / crypto
    "JWT_ALGORITHM_DEFAULT",
    # Timeouts
    "DEFAULT_HTTP_TIMEOUT",
    "DEFAULT_WEBHOOK_TIMEOUT",
    "DEFAULT_KPI_FETCH_TIMEOUT",
    "DEFAULT_ES_TIMEOUT",
    "DEFAULT_THEHIVE_TIMEOUT",
    "DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT",
    "DEFAULT_BACKUP_TIMEOUT",
    "DEFAULT_TEST_TIMEOUT",
    # Query/page sizes
    "DEFAULT_ALERT_QUERY_LIMIT",
    "DEFAULT_SANITIZATION_MAX_LENGTH",
    "DEFAULT_ES_SEARCH_SIZE",
    "DEFAULT_KPI_SEARCH_SIZE",
    # Service URLs
    "DEFAULT_SHUFFLE_BACKEND_URL",
    "DEFAULT_SHUFFLE_FRONTEND_URL",
    "DEFAULT_OPENSEARCH_URL",
    "DEFAULT_ELASTICSEARCH_URL",
    "DEFAULT_OPENSEARCH_HOST_URL",
    "SHUFFLE_WEBHOOK_TEMPLATE",
    "SHUFFLE_WEBHOOK_DEFAULT",
    # Webhook info paths
    "WEBHOOK_INFO_PATHS",
    # Docker
    "DEFAULT_DOCKER_SOCKET_MODE",
    # Secret lengths
    "SECRET_LENGTH_API_KEY",
    "SECRET_LENGTH_PASSWORD",
    "SECRET_LENGTH_TOKEN",
    "SECRET_LENGTH_JWT",
    "SECRET_LENGTH_WEBHOOK_TOKEN",
    # Environment variable names
    "ENV_ELASTIC_PASSWORD",
    "ENV_THEHIVE_API_KEY",
    "ENV_CORTEX_API_KEY",
    "ENV_SHUFFLE_API_KEY",
    "ENV_JWT_SECRET_KEY",
    "ENV_JWT_ALGORITHM",
    "ENV_JWT_EXPIRATION_MINUTES",
    "ENV_POSTGRES_PASSWORD",
    "ENV_REDIS_PASSWORD",
    "ENV_SHUFFLE_DEFAULT_PASSWORD",
    "ENV_SIEM_WEBHOOK_TOKEN",
    "ENV_EDR_SIM_TOKEN",
    "ENV_FIREWALL_SIM_TOKEN",
    "ENV_THEHIVE_SECRET",
    "ENV_CORTEX_SECRET",
    "ENV_SHUFFLE_PIPELINE_AUTH",
    "ENV_MISP_DB_ROOT_PASSWORD",
    "ENV_MISP_DB_PASSWORD",
    "ENV_MISP_ADMIN_PASSWORD",
    "ENV_MISP_ENCRYPTION_KEY",
    "ENV_MISP_SALT",
    "ENV_GRAFANA_ADMIN_PASSWORD",
    "ENV_GRAFANA_DB_PASSWORD",
    "ENV_WEB_UI_PASSWORD",
    "ENV_API_AUTH_SECRET",
    "CRITICAL_CREDENTIAL_ENV_VARS",
    # Shuffle-specific defaults
    "DEFAULT_SHUFFLE_TIMEOUT",
    "DEFAULT_SHUFFLE_POOL_SIZE",
    "DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT",
    "DEFAULT_SHUFFLE_PROBE_TIMEOUT",
    "DEFAULT_SHUFFLE_QUICK_TIMEOUT",
    # Base HTTP client defaults
    "DEFAULT_TIMEOUT",
    "DEFAULT_RETRIES",
    "DEFAULT_BACKOFF",
    "DEFAULT_POOL_SIZE",
    "DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
    "DEFAULT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
    # Analytics defaults
    "DEFAULT_ANALYTICS_SEARCH_SIZE",
    "DEFAULT_NODE_TIMING_TIMEOUT",
    # API rate limits and version
    "DEFAULT_RATE_LIMIT_PER_MINUTE",
    "DEFAULT_RATE_LIMIT_PER_HOUR",
    "DEFAULT_RATE_LIMIT_PER_DAY",
    "DEFAULT_API_VERSION",
    # Mock metric values
    "MOCK_METRICS_CPU",
    "MOCK_METRICS_MEMORY",
    "MOCK_METRICS_DISK",
    # Alert ID validation
    "ALERT_ID_PATTERN",
    # Credential validation
    "PLACEHOLDER_VALUES",
]

# ---------------------------------------------------------------------------
# Elasticsearch / OpenSearch index names
# ---------------------------------------------------------------------------
METRICS_INDEX = "soar-metrics"
ALERTS_INDEX = "soar-alerts"

# Shuffle execution index (managed by Shuffle/OpenSearch internally)
SHUFFLE_EXECUTION_INDEX = "workflowexecution-000001"

# ---------------------------------------------------------------------------
# Service names (used as dict keys, log tags, health-check identifiers)
# ---------------------------------------------------------------------------
SERVICE_THEHIVE = "thehive"
SERVICE_CORTEX = "cortex"
SERVICE_MISP = "misp"
SERVICE_SHUFFLE = "shuffle"
SERVICE_ELASTICSEARCH = "elasticsearch"

# ---------------------------------------------------------------------------
# HTTP headers and content types
# ---------------------------------------------------------------------------
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
HEADER_TRACE_ID = "X-Request-ID"

CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_NDJSON = "application/x-ndjson"

AUTH_BEARER_PREFIX = "Bearer"
AUTH_BASIC_PREFIX = "Basic"

# ---------------------------------------------------------------------------
# JWT / crypto algorithms
# ---------------------------------------------------------------------------
JWT_ALGORITHM_DEFAULT = "HS256"

# ---------------------------------------------------------------------------
# Default HTTP request timeouts (seconds)
# ---------------------------------------------------------------------------
DEFAULT_HTTP_TIMEOUT = 30
DEFAULT_WEBHOOK_TIMEOUT = 30
DEFAULT_KPI_FETCH_TIMEOUT = 10
DEFAULT_ES_TIMEOUT = 10
DEFAULT_THEHIVE_TIMEOUT = 120
DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT = 300

# ---------------------------------------------------------------------------
# Default subprocess / backup timeouts (seconds)
# ---------------------------------------------------------------------------
DEFAULT_BACKUP_TIMEOUT = 600
DEFAULT_TEST_TIMEOUT = 300

# ---------------------------------------------------------------------------
# Default query/page sizes
# ---------------------------------------------------------------------------
DEFAULT_ALERT_QUERY_LIMIT = 100
DEFAULT_SANITIZATION_MAX_LENGTH = 1000
DEFAULT_ES_SEARCH_SIZE = 1000
DEFAULT_KPI_SEARCH_SIZE = 10000

# ---------------------------------------------------------------------------
# Default service URLs (Docker internal network)
# ---------------------------------------------------------------------------
DEFAULT_SHUFFLE_BACKEND_URL = "http://shuffle-backend:5001"
DEFAULT_SHUFFLE_FRONTEND_URL = "http://shuffle-frontend"
DEFAULT_OPENSEARCH_URL = "http://opensearch:9200"
DEFAULT_ELASTICSEARCH_URL = "http://elasticsearch:9200"
DEFAULT_OPENSEARCH_HOST_URL = "http://localhost:8201"

# Shuffle webhook URL template (token is appended at runtime)
SHUFFLE_WEBHOOK_TEMPLATE = DEFAULT_SHUFFLE_BACKEND_URL + "/api/v1/hooks/{token}"
SHUFFLE_WEBHOOK_DEFAULT = DEFAULT_SHUFFLE_FRONTEND_URL + "/api/v1/hooks/webhook"

# ---------------------------------------------------------------------------
# Webhook info file locations (searched in order)
# ---------------------------------------------------------------------------
WEBHOOK_INFO_PATHS = (
    "/app/reports/validation/results/webhook_info.json",
    "/app/runtime/results/webhook_info.json",
    "/app/results/webhook_info.json",
    "/app/webhook_info.json",
)

# ---------------------------------------------------------------------------
# Docker socket
# ---------------------------------------------------------------------------
DEFAULT_DOCKER_SOCKET_MODE = 777

# ---------------------------------------------------------------------------
# Secret generation key lengths
# ---------------------------------------------------------------------------
SECRET_LENGTH_API_KEY = 64
SECRET_LENGTH_PASSWORD = 32
SECRET_LENGTH_TOKEN = 48
SECRET_LENGTH_JWT = 64
SECRET_LENGTH_WEBHOOK_TOKEN = 64

# ---------------------------------------------------------------------------
# Environment variable names (used in validate_credentials, cli, etc.)
# ---------------------------------------------------------------------------
ENV_ELASTIC_PASSWORD = "ELASTIC_PASSWORD"
ENV_THEHIVE_API_KEY = "THEHIVE_API_KEY"
ENV_CORTEX_API_KEY = "CORTEX_API_KEY"
ENV_SHUFFLE_API_KEY = "SHUFFLE_DEFAULT_APIKEY"
ENV_JWT_SECRET_KEY = "JWT_SECRET_KEY"
ENV_JWT_ALGORITHM = "JWT_ALGORITHM"
ENV_JWT_EXPIRATION_MINUTES = "JWT_EXPIRATION_MINUTES"
ENV_POSTGRES_PASSWORD = "POSTGRES_PASSWORD"
ENV_REDIS_PASSWORD = "REDIS_PASSWORD"
ENV_SHUFFLE_DEFAULT_PASSWORD = "SHUFFLE_DEFAULT_PASSWORD"
ENV_SIEM_WEBHOOK_TOKEN = "SIEM_WEBHOOK_TOKEN"
ENV_EDR_SIM_TOKEN = "EDR_SIM_TOKEN"
ENV_FIREWALL_SIM_TOKEN = "FIREWALL_SIM_TOKEN"
ENV_THEHIVE_SECRET = "THEHIVE_SECRET"
ENV_CORTEX_SECRET = "CORTEX_SECRET"
ENV_SHUFFLE_PIPELINE_AUTH = "SHUFFLE_PIPELINE_AUTH"
ENV_MISP_DB_ROOT_PASSWORD = "MISP_DB_ROOT_PASSWORD"
ENV_MISP_DB_PASSWORD = "MISP_DB_PASSWORD"
ENV_MISP_ADMIN_PASSWORD = "MISP_ADMIN_PASSWORD"
ENV_MISP_ENCRYPTION_KEY = "MISP_ENCRYPTION_KEY"
ENV_MISP_SALT = "MISP_SALT"
ENV_GRAFANA_ADMIN_PASSWORD = "GRAFANA_ADMIN_PASSWORD"
ENV_GRAFANA_DB_PASSWORD = "GRAFANA_DB_PASSWORD"
ENV_WEB_UI_PASSWORD = "WEB_UI_PASSWORD"
ENV_API_AUTH_SECRET = "API_AUTH_SECRET"

# Tuple of all critical credential env vars (for validate_credentials)
CRITICAL_CREDENTIAL_ENV_VARS = (
    ENV_ELASTIC_PASSWORD,
    ENV_THEHIVE_SECRET,
    ENV_THEHIVE_API_KEY,
    ENV_CORTEX_SECRET,
    ENV_CORTEX_API_KEY,
    ENV_SHUFFLE_DEFAULT_PASSWORD,
    ENV_SHUFFLE_API_KEY,
    ENV_SHUFFLE_PIPELINE_AUTH,
    ENV_POSTGRES_PASSWORD,
    ENV_REDIS_PASSWORD,
    ENV_MISP_DB_ROOT_PASSWORD,
    ENV_MISP_DB_PASSWORD,
    ENV_MISP_ADMIN_PASSWORD,
    ENV_MISP_ENCRYPTION_KEY,
    ENV_MISP_SALT,
    ENV_GRAFANA_ADMIN_PASSWORD,
    ENV_GRAFANA_DB_PASSWORD,
    ENV_WEB_UI_PASSWORD,
    ENV_API_AUTH_SECRET,
    ENV_SIEM_WEBHOOK_TOKEN,
    ENV_EDR_SIM_TOKEN,
    ENV_FIREWALL_SIM_TOKEN,
)

# ---------------------------------------------------------------------------
# Shuffle-specific defaults (shared by shuffle_helpers and shuffle_es_helpers)
# ---------------------------------------------------------------------------
DEFAULT_SHUFFLE_TIMEOUT = DEFAULT_HTTP_TIMEOUT
DEFAULT_SHUFFLE_POOL_SIZE = 50
DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT = DEFAULT_KPI_SEARCH_SIZE
DEFAULT_SHUFFLE_PROBE_TIMEOUT = 10
DEFAULT_SHUFFLE_QUICK_TIMEOUT = 5

# ---------------------------------------------------------------------------
# Base HTTP client defaults (shared by all integration clients)
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.5
DEFAULT_POOL_SIZE = 50
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
DEFAULT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30.0

# ---------------------------------------------------------------------------
# Analytics defaults
# ---------------------------------------------------------------------------
DEFAULT_ANALYTICS_SEARCH_SIZE = 100
DEFAULT_NODE_TIMING_TIMEOUT = 30

# ---------------------------------------------------------------------------
# API rate limits and version
# ---------------------------------------------------------------------------
DEFAULT_RATE_LIMIT_PER_MINUTE = 100
DEFAULT_RATE_LIMIT_PER_HOUR = 5000
DEFAULT_RATE_LIMIT_PER_DAY = 50000
DEFAULT_API_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Mock metric values (used by route_helpers for fallback responses)
# ---------------------------------------------------------------------------
MOCK_METRICS_CPU = 50.0
MOCK_METRICS_MEMORY = 60.0
MOCK_METRICS_DISK = 70.0

# ---------------------------------------------------------------------------
# Alert ID validation pattern
# ---------------------------------------------------------------------------
ALERT_ID_PATTERN = r"^ALERT-\d{10}-\d{4}$"

# ---------------------------------------------------------------------------
# Placeholder values for credential validation
# ---------------------------------------------------------------------------
PLACEHOLDER_VALUES = frozenset(
    v.lower()
    for v in (
        "",
        "CHANGE_ME",
        "CHANGEME",
        "***CHANGEME***",
        "changeme",
        "DEFAULT",
        "PASSWORD",
        "SECRET",
        "ADMIN",
        "123456",
        "QWERTY",
        "PASSWORD123",
        "12345678",
        "TOOR",
        "LETMEIN",
        "XXX",
        "FIXME",
        "TODO",
        "EXAMPLE",
        "SAMPLE",
        "TEST",
        "TEST123",
        "NULL",
        "NONE",
        "N/A",
        "NA",
        "TBD",
        "PLACEHOLDER",
        "YOUR_PASSWORD_HERE",
        "INSERT_PASSWORD",
        "REPLACE_ME",
    )
)
