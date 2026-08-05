"""
Script para generar datos simulados de rendimiento y calcular KPIs
"""
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from soar_lab.domain.statistical_calculator import StatisticalCalculator


def generate_simulated_alerts(num_alerts: int = 100) -> List[Dict[str, Any]]:
    """Genera datos simulados de alertas"""
    alerts = []
    base_time = datetime.now() - timedelta(hours=24)

    for i in range(num_alerts):
        # Tiempo de procesamiento: entre 30 segundos y 5 minutos
        processing_time = random.uniform(30, 300)

        # Tiempo de respuesta MTTR: entre 5 minutos y 2 horas
        mttr = random.uniform(300, 7200)

        # Severidad: 1 (low), 2 (medium), 3 (high)
        severity = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]

        # Éxito: 95% de éxito
        success = random.random() < 0.95

        alert = {
            "alert_id": f"alert_{i:04d}",
            "timestamp": (base_time + timedelta(seconds=i * 864)).isoformat(),
            "severity": severity,
            "processing_time": processing_time,
            "mttr": mttr if success else None,
            "success": success,
            "thehive_case_created": success,
            "cortex_analyzed": success,
            "misp_searched": success,
            "es_indexed": success,
            "wazuh_queried": success
        }
        alerts.append(alert)

    return alerts


def calculate_kpis(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula KPIs usando StatisticalCalculator"""
    statistical_calculator = StatisticalCalculator()

    # Extraer datos para cálculos
    processing_times = [alert["processing_time"] for alert in alerts]
    mttr_values = [alert["mttr"] for alert in alerts if alert["mttr"] is not None]
    success_count = sum(1 for alert in alerts if alert["success"])
    total_count = len(alerts)

    # Calcular estadísticas de tiempo de procesamiento
    processing_stats = statistical_calculator.calculate_statistical_metrics(processing_times)

    # Calcular estadísticas de MTTR
    mttr_stats = statistical_calculator.calculate_statistical_metrics(mttr_values) if mttr_values else {}

    # Calcular success rate directamente
    success_rate = (success_count / total_count) if total_count > 0 else 0

    # Calcular promedio MTTR directamente
    avg_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0

    # Calcular percentiles directamente (usando los valores de statistical_calculator)
    p50_mttr = mttr_stats.get("p50", 0) if mttr_stats else 0
    p95_mttr = mttr_stats.get("p90", 0) if mttr_stats else 0  # p90 como aproximación de p95
    p99_mttr = mttr_stats.get("max", 0) if mttr_stats else 0  # max como aproximación de p99

    # Calcular percentiles de tiempo de procesamiento
    p50_processing = processing_stats.get("p50", 0)
    p95_processing = processing_stats.get("p90", 0)  # p90 como aproximación de p95
    p99_processing = processing_stats.get("max", 0)  # max como aproximación de p99

    return {
        "total_alerts": total_count,
        "successful_alerts": success_count,
        "success_rate": success_rate,
        "processing_time": {
            "mean": processing_stats.get("mean", 0),
            "median": processing_stats.get("median", 0),
            "std_dev": processing_stats.get("std_dev", 0),
            "min": processing_stats.get("min", 0),
            "max": processing_stats.get("max", 0),
            "p50": p50_processing,
            "p95": p95_processing,
            "p99": p99_processing
        },
        "mttr": {
            "mean": avg_mttr,
            "median": mttr_stats.get("median", 0) if mttr_stats else 0,
            "std_dev": mttr_stats.get("std_dev", 0) if mttr_stats else 0,
            "min": mttr_stats.get("min", 0) if mttr_stats else 0,
            "max": mttr_stats.get("max", 0) if mttr_stats else 0,
            "p50": p50_mttr,
            "p95": p95_mttr,
            "p99": p99_mttr
        },
        "service_success_rates": {
            "thehive": sum(1 for a in alerts if a["thehive_case_created"]) / total_count if total_count > 0 else 0,
            "cortex": sum(1 for a in alerts if a["cortex_analyzed"]) / total_count if total_count > 0 else 0,
            "misp": sum(1 for a in alerts if a["misp_searched"]) / total_count if total_count > 0 else 0,
            "elasticsearch": sum(1 for a in alerts if a["es_indexed"]) / total_count if total_count > 0 else 0,
            "wazuh": sum(1 for a in alerts if a["wazuh_queried"]) / total_count if total_count > 0 else 0
        }
    }


def main():
    """Función principal"""
    print("Generando datos simulados de alertas...")
    alerts = generate_simulated_alerts(100)

    print("Calculando KPIs...")
    kpis = calculate_kpis(alerts)

    print("\n=== KPIs Calculados ===")
    print(json.dumps(kpis, indent=2))

    # Guardar resultados en un archivo JSON
    output_file = "src/soar_lab/infrastructure/artifacts/kpi_results.json"
    with open(output_file, "w") as f:
        json.dump(kpis, f, indent=2)

    print(f"\nResultados guardados en: {output_file}")


if __name__ == "__main__":
    main()
