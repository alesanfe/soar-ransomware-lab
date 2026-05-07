
up:
	docker compose -f docker/docker-compose.yml --env-file docker/.env up -d

down:
	docker compose -f docker/docker-compose.yml --env-file docker/.env down

restart:
	docker compose -f docker/docker-compose.yml --env-file docker/.env restart

logs:
	docker compose -f docker/docker-compose.yml --env-file docker/.env logs -f

ps:
	docker compose -f docker/docker-compose.yml --env-file docker/.env ps

health:
	@echo "Checking service health..."
	@curl -f http://localhost:9000/api/health && echo "TheHive: OK" || echo "TheHive: FAILED"
	@curl -f http://localhost:9001/api/health && echo "Cortex: OK" || echo "Cortex: FAILED"
	@curl -f http://localhost:5001/health && echo "Shuffle: OK" || echo "Shuffle: FAILED"
	@curl -f http://localhost:19200/_cluster/health && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"

test:
	python3 scripts/send_alert.py

test-malicious:
	python3 scripts/send_alert.py --type malicious --single

test-benign:
	python3 scripts/send_alert.py --type benign --single

test-batch:
	python3 scripts/send_alert.py --type malicious --num-alerts 10 --delay 5

metrics:
	python3 scripts/calc_kpis.py

# Enhanced metrics with data generation
metrics-full:
	@echo "🔄 Generating complete metrics analysis..."
	python3 scripts/tfm_data_enhancer.py --complete
	python3 scripts/calc_kpis.py

backup:
	bash scripts/backup.sh

restore:
	@echo "Usage: make restore BACKUP=<backup_name>"
	@echo "Available backups:"
	@ls -1 backups/ | grep -E "_manifest.txt$" | sed 's/_manifest.txt//' || echo "No backups found"

clean:
	docker compose -f docker/docker-compose.yml --env-file docker/.env down -v

clean-all:
	docker compose -f docker/docker-compose.yml --env-file docker/.env down -v --remove-orphans
	docker system prune -f

certs:
	bash scripts/gen_certs.sh

deps:
	python3 -m pip install --upgrade pip
	pip3 install requests jsonschema

deps-test:
	pip3 install -r requirements-test.txt

generate-secrets:
	python3 scripts/generate_secrets.py

scan-vulnerabilities:
	bash scripts/scan_vulnerabilities.sh

auto-backup:
	bash scripts/auto_backup.sh

setup-backup-schedule:
	bash scripts/auto_backup.sh -s "0 2 * * *"

check-deps:
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || echo "❌ Docker not found"
	@command -v docker compose >/dev/null 2>&1 || echo "❌ Docker Compose not found"
	@command -v python3 >/dev/null 2>&1 || echo "❌ Python3 not found"
	@command -v openssl >/dev/null 2>&1 || echo "❌ OpenSSL not found"
	@echo "✅ All dependencies installed"

# Data Analysis Commands
data-status:
	@echo "📊 Checking data availability status..."
	python3 scripts/tfm_data_viewer.py --status

data-generate:
	@echo "🔄 Generating complete analysis data..."
	python3 scripts/tfm_data_enhancer.py --complete

data-view:
	@echo "📈 Viewing all available data..."
	python3 scripts/tfm_data_viewer.py --all

data-watch:
	@echo "👀 Monitoring data changes in real-time..."
	python3 scripts/tfm_data_viewer.py --watch

data-export:
	@echo "💾 Exporting analysis data to JSON..."
	python3 scripts/tfm_data_viewer.py --export

test-unit:
	python3 -m pytest tests/unit/ -v

test-atomic:
	python3 -m pytest tests/atomic/ -v

test-security:
	python3 -m pytest tests/security/ -v

test-integration:
	python3 -m pytest tests/integration/ -v

test-performance:
	python3 -m pytest tests/performance/ -v

test-e2e:
	python3 -m pytest tests/e2e/ -v

test-all:
	bash scripts/run_tests.sh

test-coverage:
	python3 -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term

help:
	@echo "SOAR Ransomware Lab - Makefile Commands"
	@echo ""
	@echo "Service Management:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View service logs"
	@echo "  make ps          - Show service status"
	@echo "  make health      - Check service health"
	@echo ""
	@echo "Testing (Functional):"
	@echo "  make test        - Run single test alert"
	@echo "  make test-malicious  - Test malicious alert"
	@echo "  make test-benign     - Test benign alert"
	@echo "  make test-batch      - Run batch test (10 alerts)"
	@echo ""
	@echo "Testing (Automated):"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-atomic    - Run atomic tests"
	@echo "  make test-security  - Run security tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-performance - Run performance tests"
	@echo "  make test-e2e       - Run E2E tests"
	@echo "  make test-all       - Run all tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Metrics & Analysis:"
	@echo "  make metrics      - Calculate KPIs from logs"
	@echo "  make metrics-full - Generate complete metrics analysis"
	@echo "  make data-status - Check data availability status"
	@echo "  make data-generate - Generate complete analysis data"
	@echo "  make data-view   - View all available data"
	@echo "  make data-watch  - Monitor data changes in real-time"
	@echo "  make data-export - Export analysis data to JSON"
	@echo ""
	@echo "Backup & Restore:"
	@echo "  make backup      - Create backup"
	@echo "  make restore     - Restore from backup (use BACKUP=<name>)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       - Stop services and remove volumes"
	@echo "  make clean-all   - Full cleanup including unused images"
	@echo "  make certs       - Generate TLS certificates"
	@echo ""
	@echo "Dependencies:"
	@echo "  make deps        - Install Python dependencies"
	@echo "  make deps-test   - Install test dependencies"
	@echo "  make check-deps  - Check if dependencies are installed"
	@echo ""
	@echo "Security:"
	@echo "  make generate-secrets    - Generate secure passwords and tokens"
	@echo "  make scan-vulnerabilities - Scan Docker images for vulnerabilities"
	@echo "  make auto-backup         - Perform automated backup"
	@echo "  make setup-backup-schedule - Setup automatic daily backup"
	@echo ""
	@echo "Other:"
	@echo "  make help        - Show this help message"
