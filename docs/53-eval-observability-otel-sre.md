# Evaluación Observabilidad — OpenTelemetry / SRE Golden Signals / ISO 27001 A.8

> **Fecha**: 2026-11-12 · **Resultado**: stack maduro verificado — SLO burn-rate + TLS-visibility ya implementados.

## Matriz por dimensión

| Dimensión | Marco | Estado verificado |
|-----------|-------|-------------------|
| **Métricas** | Golden Signals | Prometheus: jobs por servicio + blackbox http/https/tcp/tls + cAdvisor (containers) + ES exporter + app `/metrics` + network-watcher. Latency/traffic/errors/saturation cubiertos (alertas por señal) |
| **Logs** | OTEL/ISO A.8 | Promtail docker_sd → Loki **TLS** (`ca_file`), pipeline de redacción de secretos (auth=, passwords, tokens, Authorization headers, webhook URLs), labels container/service/network/compose |
| **Trazas** | OpenTelemetry | OTEL Collector → Tempo; instrumentación app OTEL; `trace_id_ctx` correlaciona logs↔trazas |
| **Retención** | ISO A.8 | Loki `retention_period: 720h` (30d) + `retention_enabled` + `delete_delay`; Prometheus `tsdb.retention.time=7d` + `size=2GB` — acotado para lab |
| **Alertado** | SRE | `alert-rules.yml` (1853 líneas, provisioning Grafana): señales golden + `obs_cert_expiry_30d` + SLO burn + disponibilidad de stack |
| **Dashboards** | — | Grafana provisioning (datasources+dashboards automontados); verificado en evaluación previa |
| **SLI/SLO** | SRE | **`obs_admission_slo_burn_rate`**: SLO 99% admission success, ventanas 5m+1h fast-burn — burn-rate alerting real, no umbrales estáticos |
| **Visibilidad TLS** | ISO A.8.24 | `probe_ssl_earliest_cert_expiry` por endpoint TLS → alertas de expiración de certs lab CA a 30d — la métrica distintiva del stack |

## Positivos destacados

- Discovery promtail via **docker-socket-proxy** (CONTAINERS/INFO whitelist — sin raw socket)
- Redacción de secretos **antes** de Loki (defensa en profundidad sobre logs)
- módulos blackbox separados por esquema (http_2xx / https_2xx con CA lab / tcp / tcp_tls)
- Positions en tmpfs (re-scan honesto tras restart, documentado)

## Residuales (diseño lab)

| Restricción | Naturaleza |
|-------------|------------|
| Retenciones cortas (7d métricas / 30d logs) | Lab single-node; producción exigiría objetos remotos (ya existe SeaweedFS/S3 para backup) |
| SLO definido solo para admission | Extensible a disponibilidad API/webhook — base existe |
| Tempo sin retention explícita | Storage local por defecto; trazas efímeras en lab |
