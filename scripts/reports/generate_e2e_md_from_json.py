#!/usr/bin/env python3
"""Generate e2e_report.md from an existing e2e_report.json.

This is a static fallback used by the docs deployment when the Docker lab
is not running. It reads the committed ``reports/e2e/e2e_report.json`` and
produces a Markdown report that embeds the charts from ``reports/e2e/charts/``.

Usage::

    python scripts/reports/generate_e2e_md_from_json.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JSON_PATH = REPO_ROOT / "reports" / "e2e" / "e2e_report.json"
CHARTS_DIR = REPO_ROOT / "reports" / "e2e" / "charts"
OUTPUT_PATH = REPO_ROOT / "reports" / "e2e" / "e2e_report.md"


def _fmt(v: object, suffix: str = "") -> str:
    """Format a value for Markdown, handling None/0 gracefully."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.1f}{suffix}"
    return f"{v}{suffix}"


def generate() -> None:
    """Generate the Markdown report from the JSON data."""
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found")
        return

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    generated_at = data.get("generated_at", now)

    lines: list[str] = [
        "---",
        "sidebar_position: 200",
        "sidebar_label: E2E Test Report",
        "description: Auto-generated E2E test report with MTTR, service health, and TFM charts.",
        "---",
        "",
        "# SOAR Ransomware Lab — Informe de Tests E2E",
        "",
        f"Generado: **{generated_at}**",
        "",
        "> Este informe está alineado con las figuras y tablas especificadas en",
        "> `docs/thesis/figures_tables_list.md` del TFM. Cada sección incluye",
        "> referencias cruzadas a las tablas (Tabla X.Y) y figuras (Figura X.Y / GE X)",
        "> correspondientes del documento de tesis.",
        "",
        "---",
        "",
        "## Tabla de Contenidos",
        "",
        "1. [Resumen Ejecutivo](#resumen-ejecutivo)",
        "2. [Salud de Servicios](#salud-de-servicios)",
        "3. [Resultados de Tests](#resultados-de-tests)",
        "4. [Métricas de Workflow](#métricas-de-workflow)",
        "5. [MTTR y Percentiles](#mttr-y-percentiles)",
        "6. [Distribución de Alertas](#distribución-de-alertas)",
        "7. [Casos TheHive](#casos-thehive)",
        "8. [Jobs Cortex](#jobs-cortex)",
        "9. [Ejecuciones de Workflow](#ejecuciones-de-workflow)",
        "10. [Métricas Loki y Promtail](#métricas-loki-y-promtail)",
        "11. [Mejoras Implementadas por Categoría](#mejoras-implementadas-por-categoría)",
        "12. [Análisis Costo-Beneficio](#análisis-costo-beneficio)",
        "13. [Índice de Gráficas (TFM)](#índice-de-gráficas-tfm)",
        "",
        "---",
        "",
    ]

    # ---- Resumen Ejecutivo ----
    test_results = data.get("test_results", {})
    tc_cases = test_results.get("test_cases", [])
    total = len(tc_cases)
    passed = sum(1 for t in tc_cases if t.get("all_passed"))
    total - passed

    metrics = data.get("soar_metrics", {})
    mttr = metrics.get("mttr", {})
    alerts = data.get("soar_alerts", {})
    services = data.get("service_health", {})
    healthy_count = sum(1 for s in services.values() if s.get("healthy"))
    total_services = len(services)

    lines.extend([
        "## Resumen Ejecutivo",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Tests E2E | {passed}/{total} PASSED ({round(passed/total*100, 1) if total else 0}%) |",
        f"| Servicios Healthy | {healthy_count}/{total_services} |",
        f"| Total Alertas Procesadas | {alerts.get('total', 0)} |",
        f"| Total Ejecuciones Workflow | {data.get('workflow_executions', {}).get('total', 0)} |",
        f"| MTTR Medio | {_fmt(mttr.get('mean_s'), 's')} |",
        f"| MTTR P50 | {_fmt(mttr.get('p50_s'), 's')} |",
        f"| MTTR P90 | {_fmt(mttr.get('p90_s'), 's')} |",
        f"| MTTR P95 | {_fmt(mttr.get('p95_s'), 's')} |",
        f"| Nodos en Workflow | {metrics.get('total_nodes', 0)} |",
        f"| Casos TheHive | {data.get('thehive_cases', {}).get('total', 0)} |",
        f"| Jobs Cortex | {data.get('cortex_jobs', {}).get('total', 0)} |",
        "",
    ])

    # ---- Salud de Servicios ----
    if services:
        lines.extend([
            "## Salud de Servicios",
            "",
        ])
        if (CHARTS_DIR / "service_health.png").exists():
            lines.extend([
                "![Estado de Salud de Servicios](./charts/service_health.png)",
                "",
                "**Gráfica — Estado de salud de los servicios del laboratorio.**",
                "Cada barra representa un servicio del stack Docker (TheHive, Cortex,",
                "Shuffle, Elasticsearch/OpenSearch, Loki, Grafana, API SOAR). La altura",
                "indica el código HTTP de respuesta (200 = healthy, >400 = degradado).",
                "El color verde señala servicios healthy y el rojo los no disponibles.",
                "",
            ])
        lines.extend([
            "| Servicio | URL | Status | Healthy |",
            "|----------|-----|--------|---------|",
        ])
        for name, info in sorted(services.items()):
            status = info.get("status_code", 0)
            healthy = "✓" if info.get("healthy") else "✗"
            url = info.get("url", "")
            lines.append(f"| {name} | {url} | {status} | {healthy} |")
        lines.append("")

    # ---- Resultados de Tests ----
    if tc_cases:
        lines.extend([
            "## Resultados de Tests",
            "",
            "| Test | Status | Duración | Pasados/Total |",
            "|------|--------|----------|---------------|",
        ])
        for tc in tc_cases:
            name = tc.get("name", "N/A")
            status = "✅ PASSED" if tc.get("all_passed") else "❌ FAILED"
            duration = _fmt(tc.get("duration_s"), "s")
            passed_n = tc.get("passed", 0)
            total_n = tc.get("total", 0)
            lines.append(f"| {name} | {status} | {duration} | {passed_n}/{total_n} |")
        lines.append("")

    # ---- Métricas de Workflow ----
    wf = data.get("workflow_executions", {})
    if wf:
        lines.extend([
            "## Métricas de Workflow",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Total ejecuciones | {wf.get('total', 0)} |",
            f"| Finalizadas | {wf.get('finished', 0)} |",
            f"| Fallidas | {wf.get('failed', 0)} |",
            f"| En ejecución | {wf.get('running', 0)} |",
            "",
        ])
        if (CHARTS_DIR / "workflow_durations.png").exists():
            lines.extend([
                "![Duración de Ejecuciones del Workflow](./charts/workflow_durations.png)",
                "",
                "**Gráfica — Duración de ejecuciones recientes del workflow.**",
                "Cada barra representa una ejecución del workflow de respuesta a",
                "ransomware, identificada por los primeros 8 caracteres del execution_id.",
                "El color verde indica ejecuciones finalizadas (FINISHED) y el rojo las",
                "fallidas. La altura muestra la duración total en segundos.",
                "",
            ])

    # ---- MTTR y Percentiles ----
    if mttr:
        lines.extend([
            "## MTTR y Percentiles",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| MTTR Promedio | {_fmt(mttr.get('mean_s'), 's')} |",
            f"| MTTR Mediana (P50) | {_fmt(mttr.get('p50_s'), 's')} |",
            f"| MTTR P90 | {_fmt(mttr.get('p90_s'), 's')} |",
            f"| MTTR P95 | {_fmt(mttr.get('p95_s'), 's')} |",
            f"| MTTR Min | {_fmt(mttr.get('min_s'), 's')} |",
            f"| MTTR Max | {_fmt(mttr.get('max_s'), 's')} |",
            f"| Desviación Estándar | {_fmt(mttr.get('std_s'), 's')} |",
            f"| N (ejecuciones) | {mttr.get('count', 0)} |",
            "",
        ])
        if (CHARTS_DIR / "Fig5_1_mttr_results.png").exists():
            lines.extend([
                "![Resultados de MTTR](./charts/Fig5_1_mttr_results.png)",
                "",
                "**Figura 5.1 — Resultados de MTTR (Manual vs SOAR).**",
                "El gráfico de barras compara el MTTR promedio, mediana (P50), P90 y P95",
                "entre la respuesta manual (baseline estimado) y la automatizada con el",
                "laboratorio SOAR. Las líneas discontinuas marcan los objetivos TFM",
                "(P50 ≤ 120 s, P90 ≤ 180 s). La automatización reduce todas las métricas",
                "por debajo de los umbrales objetivo.",
                "",
            ])
        if (CHARTS_DIR / "GE2_percentiles.png").exists():
            lines.extend([
                "![Percentiles de MTTR SOAR](./charts/GE2_percentiles.png)",
                "",
                "**Figura GE2 — Distribución de percentiles del MTTR SOAR.**",
                "El boxplot muestra la distribución completa del MTTR: min, P25, P50",
                "(mediana), P75, media, P90, P95 y P99. Las líneas discontinuas marcan",
                "los objetivos TFM (P50 ≤ 120 s en rojo, P90 ≤ 180 s en naranja).",
                "",
            ])
        if (CHARTS_DIR / "threshold_compliance.png").exists():
            lines.extend([
                "![Cumplimiento de Objetivos](./charts/threshold_compliance.png)",
                "",
                "**Gráfica — Cumplimiento de umbrales TFM.**",
                "Cada barra muestra el valor medido frente al objetivo para las métricas",
                "clave: MTTR P50, MTTR P90, tasa de éxito, dataset mínimo y reducción",
                "de MTTR. El color verde indica cumplimiento y el rojo incumplimiento.",
                "",
            ])

    # ---- Distribución de Alertas ----
    if alerts:
        lines.extend([
            "## Distribución de Alertas",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Total alertas | {alerts.get('total', 0)} |",
            "",
        ])
        if (CHARTS_DIR / "alert_distribution.png").exists():
            lines.extend([
                "![Distribución de Alertas](./charts/alert_distribution.png)",
                "",
                "**Gráfica — Distribución de alertas por tipo.**",
                "El gráfico de barras muestra el número de alertas procesadas por el",
                "sistema SOAR, desglosadas por tipo (ransomware, credential_leak,",
                "lateral_movement, etc.). Permite identificar qué tipos de incidentes",
                "son más frecuentes en el entorno de prueba.",
                "",
            ])
        if (CHARTS_DIR / "severity_distribution.png").exists():
            lines.extend([
                "![Distribución por Severidad](./charts/severity_distribution.png)",
                "",
                "**Gráfica — Distribución de alertas por severidad.**",
                "El gráfico circular muestra la proporción de alertas por nivel de",
                "severidad (critical, high, medium, low). Las alertas critical y high",
                "deben priorizarse en el playbook de respuesta automatizada.",
                "",
            ])

    # ---- Casos TheHive ----
    thehive = data.get("thehive_cases", {})
    if thehive:
        lines.extend([
            "## Casos TheHive",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Total casos | {thehive.get('total', 0)} |",
            "",
        ])
        if (CHARTS_DIR / "thehive_case_status.png").exists():
            lines.extend([
                "![Estado de Casos en TheHive](./charts/thehive_case_status.png)",
                "",
                "**Gráfica — Estado de casos en TheHive.**",
                "El gráfico de barras muestra el número de casos abiertos en TheHive",
                "agrupados por estado (Open, In Progress, Resolved, Closed). Permite",
                "verificar que el playbook crea y cierra casos correctamente durante",
                "las ejecuciones E2E.",
                "",
            ])

    # ---- Jobs Cortex ----
    cortex = data.get("cortex_jobs", {})
    if cortex:
        lines.extend([
            "## Jobs Cortex",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Total jobs | {cortex.get('total', 0)} |",
            "",
        ])

    # ---- Ejecuciones de Workflow ----
    if wf and wf.get("recent_executions"):
        lines.extend([
            "## Ejecuciones de Workflow",
            "",
            "| Execution ID | Status | Duración (s) |",
            "|-------------|--------|---------------|",
        ])
        for ex in wf["recent_executions"][:10]:
            eid = ex.get("execution_id", "N/A")[:12]
            status = ex.get("status", "N/A")
            dur = _fmt(ex.get("duration_s"), "s")
            lines.append(f"| {eid} | {status} | {dur} |")
        lines.append("")

    # ---- Métricas Loki y Promtail ----
    loki = data.get("loki_metrics", {})
    promtail = data.get("promtail_metrics", {})
    if loki or promtail:
        lines.extend([
            "## Métricas Loki y Promtail",
            "",
        ])
        if (CHARTS_DIR / "loki_log_volume.png").exists():
            lines.extend([
                "![Volumen de Logs en Loki](./charts/loki_log_volume.png)",
                "",
                "**Gráfica — Volumen de logs ingeridos por Loki.**",
                "El gráfico de líneas muestra el volumen de logs ingeridos por Loki",
                "a lo largo del tiempo, desglosado por servicio (soar-api, thehive,",
                "cortex, shuffle, etc.). Permite verificar que Promtail recopila",
                "logs de todos los componentes del laboratorio.",
                "",
            ])

    # ---- Mejoras Implementadas por Categoría ----
    lines.extend([
        "## Mejoras Implementadas por Categoría",
        "",
    ])
    if (CHARTS_DIR / "Fig5_2_improvements_category.png").exists():
        lines.extend([
            "![Mejoras por Categoría](./charts/Fig5_2_improvements_category.png)",
            "",
            "**Figura 5.2 — Mejoras identificadas vs implementadas por categoría.**",
            "El gráfico de barras agrupadas (izquierda) compara las mejoras",
            "identificadas (barra gris) frente a las implementadas (barra de color)",
            "en las cuatro categorías del proyecto: seguridad, automatización,",
            "calidad de código y monitoreo. El gráfico circular (derecha) muestra",
            "la distribución porcentual de las 44 mejoras implementadas.",
            "",
        ])
    if (CHARTS_DIR / "GE5_improvements.png").exists():
        lines.extend([
            "![Impacto de Mejoras](./charts/GE5_improvements.png)",
            "",
            "**Figura GE5 — Impacto de mejoras implementadas.**",
            "Versión alternativa del análisis de mejoras, mostrando el impacto",
            "relativo de cada categoría en la reducción del MTTR y la calidad",
            "del sistema.",
            "",
        ])

    # ---- Análisis Costo-Beneficio ----
    lines.extend([
        "## Análisis Costo-Beneficio",
        "",
    ])
    if (CHARTS_DIR / "Fig5_5_cost_benefit.png").exists():
        lines.extend([
            "![Costo-Beneficio](./charts/Fig5_5_cost_benefit.png)",
            "",
            "**Figura 5.5 — Comparación de costos y beneficios (3 años).**",
            "El gráfico compara cinco soluciones SOAR (manual, open source, híbrido,",
            "XSOAR, Resilient) en costo anual, MTTR promedio y ROI a 3 años. La",
            "solución open source de este proyecto ofrece el menor costo y mayor ROI.",
            "",
        ])
    if (CHARTS_DIR / "GE6_cost_benefit.png").exists():
        lines.extend([
            "![Costo-Beneficio (GE6)](./charts/GE6_cost_benefit.png)",
            "",
            "**Figura GE6 — Análisis costo-beneficio comparativo.**",
            "Versión simplificada del análisis costo-beneficio, enfocada en el",
            "MTTR promedio y el costo anual de cada solución.",
            "",
        ])

    # ---- Índice de Gráficas (TFM) ----
    lines.extend([
        "## Índice de Gráficas (TFM)",
        "",
        "Las siguientes gráficas están alineadas con las figuras y tablas",
        "especificadas en `docs/thesis/figures_tables_list.md`:",
        "",
        "| Gráfica | Figura TFM | Descripción |",
        "|---------|-----------|-------------|",
        "| `Fig1_3_mttr_comparison.png` | Figura 1.3 | Comparación MTTR Manual vs Automatizado |",
        "| `Fig5_1_mttr_results.png` | Figura 5.1 | Gráficos comparativos de resultados MTTR |",
        "| `Fig5_2_improvements_category.png` | Figura 5.2 | Mejoras implementadas por categoría |",
        "| `Fig5_5_cost_benefit.png` | Figura 5.5 | Comparación de costos y beneficios |",
        "| `GE1_component_timings.png` | GE1 | Tiempos de respuesta por componente |",
        "| `GE2_percentiles.png` | GE2 | Percentiles de rendimiento MTTR |",
        "| `GE3_success_rates.png` | GE3 | Tasas de éxito por tipo de alerta |",
        "| `GE4_metrics_evolution.png` | GE4 | Evolución temporal de métricas |",
        "| `GE5_improvements.png` | GE5 | Impacto de mejoras implementadas |",
        "| `GE6_cost_benefit.png` | GE6 | Análisis costo-beneficio |",
        "| `service_health.png` | — | Estado de salud de servicios |",
        "| `alert_distribution.png` | — | Distribución de alertas por tipo |",
        "| `severity_distribution.png` | — | Distribución de alertas por severidad |",
        "| `thehive_case_status.png` | — | Estado de casos en TheHive |",
        "| `workflow_durations.png` | — | Duración de ejecuciones del workflow |",
        "| `threshold_compliance.png` | — | Cumplimiento de umbrales TFM |",
        "| `loki_log_volume.png` | — | Volumen de logs en Loki |",
        "",
        "---",
        "",
        f"> Informe generado desde `reports/e2e/e2e_report.json` el {now}.",
        "> Para regenerar con datos en tiempo real, ejecutar `make test-e2e-report`",
        "> con el laboratorio Docker en ejecución.",
        "",
    ])

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {OUTPUT_PATH}")
    print(f"Lines: {len(lines)}")


if __name__ == "__main__":
    generate()
