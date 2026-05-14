
.PHONY: help install install-dev test lint format clean build docker-build docker-run docker-stop
.PHONY: up down restart logs ps health
.PHONY: test-unit test-int test-e2e test-atomic test-security test-performance test-all test-coverage
.PHONY: test-malicious test-benign test-batch
.PHONY: metrics metrics-full backup restore
.PHONY: clean clean-full clean-all clean-generated clean-docker
.PHONY: certs deps deps-test generate-secrets scan-vulnerabilities auto-backup setup-backup-schedule check-deps
.PHONY: data-status data-generate data-view data-watch data-export

help:
	@echo "SOAR Ransomware Lab - Makefile Commands"
	@echo ""
	@echo "=== Service Management ==="
	@echo "  make up          - Start services (Elasticsearch, TheHive, Cortex, Shuffle, Redis, Nginx, Wazuh)"
	@echo "  make down        - Stop services and remove volumes"
	@echo "  make restart     - Restart services"
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

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

build:
	python -m build

docker-build:
	docker build -t soar-lab-api -f apps/api/Dockerfile .

docker-run:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full up -d

docker-stop:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full down

dev-setup: install-dev
	pre-commit install
	docker compose -f infra/docker/docker-compose.yml --env-file .env.full ps

# Service Management
up:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full up -d
	@echo "Services started"

down:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full down -v --remove-orphans
	@echo "Services stopped and volumes removed"

restart:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full restart
	@echo "Services restarted"

logs:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full logs -f

ps:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full ps

health:
	@echo "Checking core service health..."
	@curl -f http://localhost:9000/api/health && echo "TheHive: OK" || echo "TheHive: FAILED"
	@curl -f http://localhost:9001/api/health && echo "Cortex: OK" || echo "Cortex: FAILED"
	@curl -f http://localhost:5001/health && echo "Shuffle: OK" || echo "Shuffle: FAILED"
	@curl -f http://localhost:9201/_cluster/health && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"

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
	@ls -1 artifacts/backups/ | grep -E "_manifest.txt$" | sed 's/_manifest.txt//' || echo "No backups found"

clean:
	find . -type d -name "__pycache__" -delete
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf artifacts/coverage/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full down -v

clean-full:
	docker-compose -f infra/docker/docker-compose.yml --env-file .env.full down -v

clean-generated:
	@echo "🧹 Cleaning generated files and artifacts..."
	@echo "Removing Python cache files..."
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "Removing Python bytecode files..."
	find . -name "*.pyc" -delete
	@echo "Removing coverage files..."
	rm -f coverage.xml .coverage
	rm -rf coverage_annotate/ htmlcov/
	@echo "Removing test result files..."
	rm -f test_results_unit.txt unit_test_results.txt
	@echo "Removing pytest cache..."
	rm -rf .pytest_cache/
	@echo "Removing temporary logs and results..."
	rm -rf artifacts/logs/ artifacts/results/ scripts/logs/ scripts/results/
	@echo "✅ Generated files cleanup completed"

clean-docker:
	@echo "🐳 Cleaning Docker artifacts..."
	docker system prune -af
	docker volume prune -f
	@echo "✅ Docker cleanup completed"

clean-all: clean-generated clean-docker
	@echo "🧹 Full project cleanup completed"

certs:
	powershell -ExecutionPolicy Bypass -File scripts/security/create-pem-cert.ps1

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

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

test-unit:
	python3 -m pytest tests/unit/ -v

test-int:
	python3 -m pytest tests/integration/ -v

test-e2e:
	python3 -m pytest tests/e2e/ -v

test-atomic:
	python3 -m pytest tests/atomic/ -v

test-security:
	python3 -m pytest tests/security/ -v

test-performance:
	python3 -m pytest tests/performance/ -v

test-all:
	bash scripts/run_tests.sh

test-coverage:
	python3 -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
