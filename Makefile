
up:
	docker compose -f docker/docker-compose.yml --env-file docker/.env up -d

down:
	docker compose -f docker/docker-compose.yml --env-file docker/.env down

test:
	python3 scripts/send_alert.py

metrics:
	python3 scripts/calc_kpis.py

clean:
	docker compose -f docker/docker-compose.yml --env-file docker/.env down -v
