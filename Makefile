
.PHONY: help install install-dev test lint format clean build docker-build docker-run docker-stop
.PHONY: up down restart logs ps health
.PHONY: test-unit test-int test-e2e test-atomic test-security test-performance test-all test-coverage
.PHONY: test-malicious test-benign test-batch
.PHONY: metrics metrics-full backup restore
.PHONY: clean clean-full clean-all clean-generated clean-docker
.PHONY: certs deps deps-test generate-secrets scan-vulnerabilities auto-backup setup-backup-schedule check-deps
.PHONY: data-status data-generate data-view data-watch data-export
.PHONY: simulate simulate-malicious simulate-benign simulate-batch
.PHONY: vagrant-up vagrant-down vagrant-ubuntu vagrant-windows vagrant-simulate

help:
	@echo "SOAR Ransomware Lab - Makefile Commands"
	@echo ""
	@echo "=== Service Management ==="
	@echo "  make up          - Start all services (Elasticsearch, TheHive, Cortex, Shuffle, Redis, Nginx, Wazuh, MISP, Loki, Promtail, Grafana)"
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
	@echo "SIEM Simulation:"
	@echo "  make simulate              - Simula ataque ransomware (5 alertas maliciosas)"
	@echo "  make simulate-malicious    - Envia 1 alerta maliciosa"
	@echo "  make simulate-benign       - Envia 1 alerta benigna"
	@echo "  make simulate-batch N=10   - Envia N alertas (default 10)"
	@echo ""
	@echo "Vagrant (multi-VM):"
	@echo "  make vagrant-up            - Levanta ambas VMs (Ubuntu SOAR + Windows victima)"
	@echo "  make vagrant-ubuntu        - Levanta solo la VM Ubuntu SOAR"
	@echo "  make vagrant-windows       - Levanta solo la VM Windows victima"
	@echo "  make vagrant-down          - Para y destruye las VMs"
	@echo "  make vagrant-simulate      - Ejecuta simulacion de ataque desde la VM Windows"
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
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d

docker-stop:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full down

dev-setup: install-dev
	pre-commit install
	docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full ps

# Service Management
up:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d
	@echo "Services started"

down:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full down -v --remove-orphans
	@echo "Services stopped and volumes removed"

restart:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full restart
	@echo "Services restarted"

logs:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full logs -f

ps:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full ps

health:
	@echo "Checking core service health..."
	@curl -f http://localhost:9000/api/health && echo "TheHive: OK" || echo "TheHive: FAILED"
	@curl -f http://localhost:9001/api/health && echo "Cortex: OK" || echo "Cortex: FAILED"
	@curl -f http://localhost:5001/health && echo "Shuffle: OK" || echo "Shuffle: FAILED"
	@curl -f http://localhost:9201/_cluster/health && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"

test:
	python3 -m soar_lab.services.send_alert

test-malicious:
	python3 -m soar_lab.services.send_alert --type malicious --single

test-benign:
	python3 -m soar_lab.services.send_alert --type benign --single

test-batch:
	python3 -m soar_lab.services.send_alert --type malicious --num-alerts 10 --delay 5

# SIEM Simulation targets
# Override from env or command line: make simulate SIMULATE_WEBHOOK=http://... SIMULATE_TOKEN=...
SIMULATE_N ?= 5
SIMULATE_DELAY ?= 3
SIMULATE_WEBHOOK ?= http://localhost:5001/api/v1/hooks/webhook
SIMULATE_TOKEN ?= SiemToken123!@#

SIEM_PYTHON ?= python3

simulate:
	@echo "==> Simulando ataque ransomware ($(SIMULATE_N) alertas maliciosas)..."
	$(SIEM_PYTHON) -m soar_lab.services.send_alert --type malicious --num-alerts $(SIMULATE_N) --delay $(SIMULATE_DELAY)

simulate-malicious:
	@echo "==> Enviando alerta maliciosa..."
	$(SIEM_PYTHON) -m soar_lab.services.send_alert --type malicious --single

simulate-benign:
	@echo "==> Enviando alerta benigna..."
	$(SIEM_PYTHON) -m soar_lab.services.send_alert --type benign --single

simulate-batch:
	@echo "==> Enviando batch de $(or $(N),10) alertas..."
	$(SIEM_PYTHON) -m soar_lab.services.send_alert --type malicious --num-alerts $(or $(N),10) --delay $(SIMULATE_DELAY)

# Vagrant targets
vagrant-up:
	cd infra/vagrant && vagrant up

vagrant-ubuntu:
	cd infra/vagrant && vagrant up soar-ubuntu

vagrant-windows:
	cd infra/vagrant && vagrant up victima-windows

vagrant-down:
	cd infra/vagrant && vagrant destroy -f

vagrant-simulate:
	cd infra/vagrant && vagrant winrm -c "powershell C:\\simulate-attack.ps1" victima-windows

metrics:
	python3 -m soar_lab.data.calc_kpis

# Enhanced metrics with data generation
metrics-full:
	@echo "Generating complete metrics analysis..."
	python3 -m soar_lab.data.calc_kpis

backup:
	curl -sf -X POST http://localhost:8000/backup/create -H "Content-Type: application/json" -d '{"description":"manual-backup"}' | python3 -m json.tool || echo "API not available — start services with 'make up' first"

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
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full down -v

clean-full:
	docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full down -v

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
	bash src/soar_lab/infrastructure/setup/gen_certs.sh
	@echo "Certificates ready in infra/docker/nginx/ssl/"

deps:
	python3 -m pip install --upgrade pip
	pip3 install requests jsonschema

deps-test:
	pip3 install -r requirements-test.txt

generate-secrets:
	python3 -m soar_lab.services.generate_secrets

scan-vulnerabilities:
	bash src/soar_lab/infrastructure/security/scan_vulnerabilities.sh

auto-backup:
	curl -sf -X POST http://localhost:8000/backup/create -H "Content-Type: application/json" -d '{"description":"auto-backup"}' | python3 -m json.tool || echo "API not available"

setup-backup-schedule:
	@echo "Schedule 'make auto-backup' via cron: 0 2 * * * cd $(PWD) && make auto-backup"

check-deps:
	@echo "Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || echo "❌ Docker not found"
	@command -v docker compose >/dev/null 2>&1 || echo "❌ Docker Compose not found"
	@command -v python3 >/dev/null 2>&1 || echo "❌ Python3 not found"
	@command -v openssl >/dev/null 2>&1 || echo "❌ OpenSSL not found"
	@echo "✅ All dependencies installed"

# Data Analysis Commands
data-status:
	@echo "Checking data availability status..."
	@ls -lh artifacts/results/ artifacts/logs/ 2>/dev/null || echo "No artifacts found — run tests first"

data-generate:
	@echo "Generating complete analysis data..."
	python3 -m soar_lab.data.calc_kpis

data-view:
	@echo "Viewing all available data..."
	@cat artifacts/results/kpis.csv 2>/dev/null || echo "No kpis.csv found — run 'make metrics' first"
	@ls artifacts/results/*.json 2>/dev/null || echo "No JSON reports found"

data-watch:
	@echo "Monitoring data changes in real-time..."
	tail -f artifacts/logs/notify.log 2>/dev/null || echo "No notify.log found — run tests first"

data-export:
	@echo "Exporting analysis data to JSON..."
	python3 -m soar_lab.data.calc_kpis --output artifacts/results/kpis_export.csv

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
	python3 -m pytest tests/ -v

test-coverage:
	python3 -m pytest tests/ --cov=src/soar_lab --cov-report=html:artifacts/coverage/htmlcov --cov-report=term
