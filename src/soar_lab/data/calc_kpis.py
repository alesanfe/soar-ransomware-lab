#!/usr/bin/env python3
"""SOAR Ransomware Lab - KPI Calculator CLI.

Reads runtime/logs/notify.log, calculates MTTR metrics and saves
the results to runtime/results/kpis.csv.

Usage:
python3 -m soar_lab.data.calc_kpis
python3 -m soar_lab.data.calc_kpis --log-file /path/to/notify.log
python3 -m soar_lab.data.calc_kpis --output /path/to/kpis.csv
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from soar_lab.common.constants import (
    DEFAULT_ELASTICSEARCH_URL,
    DEFAULT_ES_SEARCH_SIZE,
    DEFAULT_ES_TIMEOUT,
    ENV_ELASTIC_PASSWORD,
    METRICS_INDEX,
)

logger = logging.getLogger(__name__)


def _fetch_mttr_from_es(es_url: str, es_user: str, es_pass: str) -> list:
    """Fetch mttr_seconds values from soar-metrics Elasticsearch index."""
    try:
        import requests as _req

        auth = (es_user, es_pass) if es_user else None
        r = _req.get(
            f"{es_url}/{METRICS_INDEX}/_search",
            auth=auth,
            timeout=DEFAULT_ES_TIMEOUT,
            json={
                "size": DEFAULT_ES_SEARCH_SIZE,
                "_source": ["mttr_seconds"],
                "query": {"exists": {"field": "mttr_seconds"}},
            },
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
        logger.warning(f"[calc_kpis] WARN: could not fetch from ES: {e}")
        return []


def _parse_args():
    """Parse command-line arguments for the KPI calculator."""
    parser = argparse.ArgumentParser(
        description="Calculate SOAR KPIs from execution logs or Elasticsearch"
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to notify.log (default: runtime/logs/notify.log)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: runtime/results/kpis.csv)",
    )
    parser.add_argument(
        "--source",
        choices=["es", "log"],
        default="es",
        help="Data source: 'es' (Elasticsearch soar-metrics, default) or 'log' (notify.log)",
    )
    return parser.parse_args()


def _resolve_paths(args, base_dir):
    """Resolve the log file and output CSV paths from args and base_dir."""
    log_file = args.log_file or str(base_dir / "runtime" / "logs" / "notify.log")
    output_path = args.output or str(base_dir / "runtime" / "results" / "kpis.csv")
    return log_file, output_path


def _fetch_es_data(args, settings):
    """Fetch execution times from Elasticsearch; return times or None to fall back to log."""
    if args.source != "es":
        return None
    es_url = (
        os.environ.get("ELASTICSEARCH_URL")
        or os.environ.get("ES_URL")
        or (settings.get("elasticsearch_url") if hasattr(settings, "get") else None)
        or DEFAULT_ELASTICSEARCH_URL
    )
    es_user = os.environ.get("ELASTIC_USER", os.environ.get("ELASTIC_USERNAME", "elastic"))
    es_pass = os.environ.get(ENV_ELASTIC_PASSWORD, os.environ.get("ELASTICSEARCH_PASSWORD", ""))
    logger.info(f"[calc_kpis] Fetching MTTR data from Elasticsearch: {es_url}/{METRICS_INDEX}")
    execution_times = _fetch_mttr_from_es(es_url, es_user, es_pass)
    if execution_times:
        logger.info(f"[calc_kpis] Found {len(execution_times)} MTTR values in Elasticsearch.")
        return execution_times, es_url, es_user, es_pass
    logger.info("[calc_kpis] No MTTR data in ES, falling back to log file.")
    args.source = "log"
    return None, es_url, es_user, es_pass


def _parse_log_data(log_file, log_parser, stat_calc):
    """Parse execution times from the notify.log file."""
    log_path = Path(log_file)
    if not log_path.exists():
        logger.warning(f"[calc_kpis] Log file not found: {log_path}")
        logger.warning(
            "[calc_kpis] Run 'make test-malicious' or 'make test-benign' " "first to generate logs."
        )
        sys.exit(1)

    logger.info(f"[calc_kpis] Reading log file: {log_path}")
    log_content = log_path.read_text(encoding="utf-8")
    alert_steps = log_parser.parse(log_content)
    if not alert_steps:
        logger.warning("[calc_kpis] No execution steps found in log file.")
        sys.exit(1)
    return stat_calc.calculate_execution_times(alert_steps)


def _enrich_from_es(metrics, es_url, es_user, es_pass):
    """Enrich metrics with aggregated ES data if available."""
    try:
        import requests as _req

        auth = (es_user, es_pass) if es_user else None
        r_agg = _req.get(
            f"{es_url}/{METRICS_INDEX}/_search",
            auth=auth,
            timeout=DEFAULT_ES_TIMEOUT,
            json={
                "size": 0,
                "aggs": {
                    "total": {"value_count": {"field": "alert_id"}},
                    "by_type": {"terms": {"field": "alert_type", "size": 10}},
                    "critical": {"filter": {"term": {"severity": 3}}},
                    "thehive_ok": {
                        "filter": {
                            "bool": {
                                "must": {"exists": {"field": "thehive_case_id"}},
                                "must_not": {"term": {"thehive_case_id": ""}},
                            }
                        }
                    },
                    "non_empty_alert_type": {
                        "filter": {
                            "bool": {
                                "must": {"exists": {"field": "alert_type"}},
                                "must_not": {"term": {"alert_type": ""}},
                            }
                        }
                    },
                },
            },
        )
        aggs = r_agg.json().get("aggregations", {})
        metrics["total_alerts"] = r_agg.json().get("hits", {}).get("total", {}).get("value", 0)
        metrics["critical_alerts"] = aggs.get("critical", {}).get("doc_count", 0)
        metrics["thehive_success"] = aggs.get("thehive_ok", {}).get("doc_count", 0)
        by_type = {b["key"]: b["doc_count"] for b in aggs.get("by_type", {}).get("buckets", [])}
        metrics["alert_types"] = str(by_type)
        if metrics["total_alerts"] and metrics["critical_alerts"] is not None:
            metrics["critical_rate_pct"] = round(
                metrics["critical_alerts"] / metrics["total_alerts"] * 100, 2
            )
    except Exception as _e:
        logger.warning(f"[calc_kpis] WARN: could not enrich metrics from ES: {_e}")


def _save_csv(metrics, output_path, kpi_formatter):
    """Save metrics to a CSV file at output_path."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    csv_content = kpi_formatter.format_csv(metrics)
    out_path.write_text(csv_content, encoding="utf-8")

    logger.info(f"[calc_kpis] KPIs saved to: {out_path}")
    for k, v in metrics.items():
        logger.info(f"  {k}: {v}")


def main() -> None:
    args = _parse_args()

    # Resolve BASE_DIR
    base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).parent.parent.parent.parent))

    log_file, output_path = _resolve_paths(args, base_dir)

    # ------------------------------------------------------------------ #
    # Bootstrap only the dependencies needed for KPI calculation          #
    # ------------------------------------------------------------------ #
    sys.path.insert(0, str(base_dir / "src"))
    os.environ.setdefault("BASE_DIR", str(base_dir))
    os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

    from soar_lab.config.settings import create_settings
    from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
    from soar_lab.domain.statistical_calculator import StatisticalCalculator
    from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
    from soar_lab.infrastructure.kpi_formatter import CSVKPIFormatter
    from soar_lab.infrastructure.log_parser import ExecutionLogParser
    from soar_lab.infrastructure.path_service import PathService

    settings = create_settings()
    config_provider = InfrastructureConfigProvider(settings)
    path_service = PathService(base_dir=base_dir, config_provider=config_provider)
    path_service.ensure_directories()

    log_parser = ExecutionLogParser()
    kpi_formatter = CSVKPIFormatter()
    stat_calc = StatisticalCalculator()
    kpi_analyzer = KPIAnalyzer(stat_calc)

    # ------------------------------------------------------------------ #
    # Obtain execution times (ES preferred, log as fallback)              #
    # ------------------------------------------------------------------ #
    es_result = _fetch_es_data(args, settings)
    if es_result is not None:
        execution_times, es_url, es_user, es_pass = es_result
    else:
        es_url = es_user = es_pass = None
        execution_times = []

    if args.source == "log":
        execution_times = _parse_log_data(log_file, log_parser, stat_calc)

    metrics = kpi_analyzer.calculate_mttr_metrics(execution_times)

    # Enrich with aggregated ES data if available
    if args.source == "es" and execution_times:
        _enrich_from_es(metrics, es_url, es_user, es_pass)

    # ------------------------------------------------------------------ #
    # Save to CSV                                                          #
    # ------------------------------------------------------------------ #
    _save_csv(metrics, output_path, kpi_formatter)


if __name__ == "__main__":
    main()
