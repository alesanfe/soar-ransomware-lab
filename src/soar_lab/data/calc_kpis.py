#!/usr/bin/env python3
"""
SOAR Ransomware Lab - KPI Calculator CLI
Reads artifacts/logs/notify.log, calculates MTTR metrics and saves
the results to artifacts/results/kpis.csv.

Usage:
    python3 -m soar_lab.data.calc_kpis
    python3 -m soar_lab.data.calc_kpis --log-file /path/to/notify.log
    python3 -m soar_lab.data.calc_kpis --output /path/to/kpis.csv
"""

import argparse
import os
import sys
from pathlib import Path


def _fetch_mttr_from_es(es_url: str, es_user: str, es_pass: str) -> list:
    """Fetch mttr_seconds values from soar-metrics Elasticsearch index."""
    try:
        import requests as _req
        auth = (es_user, es_pass) if es_user else None
        r = _req.get(
            f"{es_url}/soar-metrics/_search",
            auth=auth,
            timeout=10,
            json={"size": 1000, "_source": ["mttr_seconds"], "query": {"exists": {"field": "mttr_seconds"}}},
        )
        hits = r.json().get("hits", {}).get("hits", [])
        times = []
        for h in hits:
            v = h.get("_source", {}).get("mttr_seconds")
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if 0 < v < 3600:
                times.append(v)
        return times
    except Exception as e:
        print(f"[calc_kpis] WARN: could not fetch from ES: {e}")
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate SOAR KPIs from execution logs or Elasticsearch")
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to notify.log (default: artifacts/logs/notify.log)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: artifacts/results/kpis.csv)",
    )
    parser.add_argument(
        "--source",
        choices=["es", "log"],
        default="es",
        help="Data source: 'es' (Elasticsearch soar-metrics, default) or 'log' (notify.log)",
    )
    args = parser.parse_args()

    # Resolve BASE_DIR
    base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).parent.parent.parent.parent))

    log_file = args.log_file or str(base_dir / "artifacts" / "logs" / "notify.log")
    output_path = args.output or str(base_dir / "artifacts" / "results" / "kpis.csv")

    # ------------------------------------------------------------------ #
    # Bootstrap only the dependencies needed for KPI calculation          #
    # ------------------------------------------------------------------ #
    sys.path.insert(0, str(base_dir / "src"))
    os.environ.setdefault("BASE_DIR", str(base_dir))
    os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

    from soar_lab.infrastructure.log_parser import ExecutionLogParser
    from soar_lab.infrastructure.kpi_formatter import CSVKPIFormatter
    from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
    from soar_lab.infrastructure.path_service import PathService
    from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
    from soar_lab.domain.statistical_calculator import StatisticalCalculator
    from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
    from soar_lab.config.settings import create_settings

    settings = create_settings()
    config_provider = InfrastructureConfigProvider(settings)
    path_service = PathService(base_dir=base_dir, config_provider=config_provider)
    path_service.ensure_directories()

    storage = FilesystemStorage(config_provider=config_provider)
    log_parser = ExecutionLogParser()
    kpi_formatter = CSVKPIFormatter()
    stat_calc = StatisticalCalculator()
    kpi_analyzer = KPIAnalyzer(stat_calc)

    # ------------------------------------------------------------------ #
    # Obtain execution times (ES preferred, log as fallback)              #
    # ------------------------------------------------------------------ #
    execution_times = []

    if args.source == "es":
        es_url = (
            os.environ.get("ELASTICSEARCH_URL")
            or os.environ.get("ES_URL")
            or (settings.get("elasticsearch_url") if hasattr(settings, "get") else None)
            or "http://elasticsearch:9200"
        )
        es_user = os.environ.get("ELASTIC_USER", os.environ.get("ELASTIC_USERNAME", "elastic"))
        es_pass = os.environ.get("ELASTIC_PASSWORD",
                                 os.environ.get("ELASTICSEARCH_PASSWORD", ""))
        print(f"[calc_kpis] Fetching MTTR data from Elasticsearch: {es_url}/soar-metrics")
        execution_times = _fetch_mttr_from_es(es_url, es_user, es_pass)
        if execution_times:
            print(f"[calc_kpis] Found {len(execution_times)} MTTR values in Elasticsearch.")
        else:
            print("[calc_kpis] No MTTR data in ES, falling back to log file.")
            args.source = "log"

    if args.source == "log":
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"[calc_kpis] Log file not found: {log_path}")
            print("[calc_kpis] Run 'make test-malicious' or 'make test-benign' first to generate logs.")
            sys.exit(1)

        print(f"[calc_kpis] Reading log file: {log_path}")
        log_content = log_path.read_text(encoding="utf-8")
        alert_steps = log_parser.parse(log_content)
        if not alert_steps:
            print("[calc_kpis] No execution steps found in log file.")
            sys.exit(1)
        execution_times = stat_calc.calculate_execution_times(alert_steps)

    metrics = kpi_analyzer.calculate_mttr_metrics(execution_times)

    # Enrich with aggregated ES data if available
    if args.source == "es" and execution_times:
        try:
            import requests as _req
            auth = (es_user, es_pass) if es_user else None
            r_agg = _req.get(
                f"{es_url}/soar-metrics/_search",
                auth=auth, timeout=10,
                json={"size": 0, "aggs": {
                    "total": {"value_count": {"field": "alert_id"}},
                    "by_type": {"terms": {"field": "alert_type", "size": 10}},
                    "critical": {"filter": {"term": {"severity": 3}}},
                    "thehive_ok": {"filter": {"bool": {
                        "must": {"exists": {"field": "thehive_case_id"}},
                        "must_not": {"term": {"thehive_case_id": ""}}
                    }}},
                    "non_empty_alert_type": {"filter": {"bool": {
                        "must": {"exists": {"field": "alert_type"}},
                        "must_not": {"term": {"alert_type": ""}}
                    }}},
                }}
            )
            aggs = r_agg.json().get("aggregations", {})
            metrics["total_alerts"] = r_agg.json().get("hits", {}).get("total", {}).get("value", 0)
            metrics["critical_alerts"] = aggs.get("critical", {}).get("doc_count", 0)
            metrics["thehive_success"] = aggs.get("thehive_ok", {}).get("doc_count", 0)
            by_type = {b["key"]: b["doc_count"] for b in aggs.get("by_type", {}).get("buckets", [])}
            metrics["alert_types"] = str(by_type)
            if metrics["total_alerts"] and metrics["critical_alerts"] is not None:
                metrics["critical_rate_pct"] = round(metrics["critical_alerts"] / metrics["total_alerts"] * 100, 2)
        except Exception as _e:
            print(f"[calc_kpis] WARN: could not enrich metrics from ES: {_e}")

    # ------------------------------------------------------------------ #
    # Save to CSV                                                          #
    # ------------------------------------------------------------------ #
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    csv_content = kpi_formatter.format_csv(metrics)
    out_path.write_text(csv_content, encoding="utf-8")

    print(f"[calc_kpis] KPIs saved to: {out_path}")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
