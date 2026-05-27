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


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate SOAR KPIs from execution logs")
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
    from soar_lab.services.kpi_analyzer import KPIAnalyzer
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
    # Read and parse the log file                                          #
    # ------------------------------------------------------------------ #
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
