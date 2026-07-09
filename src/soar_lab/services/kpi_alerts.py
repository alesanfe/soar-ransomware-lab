"""
KPI-based Alerting System
Monitors KPIs and sends alerts when thresholds are exceeded.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class KPIAlertManager:
    """Manages KPI-based alerts."""

    def __init__(self, elasticsearch_client, webhook_url: Optional[str] = None):
        """
        Initialize with Elasticsearch client and optional webhook URL.
        
        Args:
            elasticsearch_client: Elasticsearch client instance
            webhook_url: Optional webhook URL for sending alerts
        """
        self.es = elasticsearch_client
        self.webhook_url = webhook_url

        # Default thresholds
        self.thresholds = {
            "mttr_seconds": 120,  # Alert if MTTR > 2 minutes
            "success_rate_percent": 90,  # Alert if success rate < 90%
            "health_score": 70,  # Alert if health score < 70
            "service_success_rate": 85  # Alert if service success rate < 85%
        }

    def check_mttr_threshold(self, hours: int = 1) -> Dict[str, Any]:
        """
        Check if MTTR exceeds threshold.
        
        Args:
            hours: Time period in hours
            
        Returns:
            Dict with alert status
        """
        try:
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                        }
                    }
                },
                "size": 10000
            }

            results = self.es.search(query=query, index="soar-metrics", size=10000)
            metrics = results.get("hits", {}).get("hits", [])

            mttr_values = []
            for hit in metrics:
                mttr = hit.get("_source", {}).get("mttr_seconds", 0)
                if mttr:
                    mttr_values.append(mttr)

            if not mttr_values:
                return {"status": "no_data", "message": "No MTTR data available"}

            avg_mttr = sum(mttr_values) / len(mttr_values)
            threshold = self.thresholds["mttr_seconds"]

            if avg_mttr > threshold:
                alert = {
                    "status": "alert",
                    "metric": "mttr_seconds",
                    "value": avg_mttr,
                    "threshold": threshold,
                    "message": f"MTTR exceeded threshold: {avg_mttr:.2f}s > {threshold}s",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self._send_alert(alert)
                return alert

            return {
                "status": "ok",
                "metric": "mttr_seconds",
                "value": avg_mttr,
                "threshold": threshold
            }

        except Exception as e:
            logger.error(f"Error checking MTTR threshold: {e}")
            return {"status": "error", "message": str(e)}

    def check_service_health(self, hours: int = 1) -> Dict[str, Any]:
        """
        Check if service success rates exceed threshold.
        
        Args:
            hours: Time period in hours
            
        Returns:
            Dict with alert status
        """
        try:
            from soar_lab.services.kpi_analyzer import KPIAnalyzer
            from soar_lab.domain.statistical_calculator import StatisticalCalculator

            # Get metrics data from ES
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                        }
                    }
                },
                "size": 10000
            }
            results = self.es.search(query=query, index="soar-metrics", size=10000)
            metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

            if not metrics_data:
                return {"status": "no_data", "message": "No metrics data available"}

            analyzer = KPIAnalyzer(StatisticalCalculator())
            kpis = analyzer.calculate_service_integration_kpis(metrics_data, hours)

            threshold = self.thresholds["service_success_rate"]
            alerts = []

            for service, data in kpis.get("services", {}).items():
                success_rate = data.get("success_rate_percent", 0)
                if success_rate < threshold and data["total"] > 0:
                    alert = {
                        "status": "alert",
                        "metric": f"service_success_rate_{service}",
                        "value": success_rate,
                        "threshold": threshold,
                        "message": f"{service} success rate below threshold: {success_rate}% < {threshold}%",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    alerts.append(alert)
                    self._send_alert(alert)

            if alerts:
                return {"status": "alert", "alerts": alerts}
            return {"status": "ok", "message": "All services healthy"}

        except Exception as e:
            logger.error(f"Error checking service health: {e}")
            return {"status": "error", "message": str(e)}

    def check_health_score(self) -> Dict[str, Any]:
        """
        Check if system health score exceeds threshold.
        
        Returns:
            Dict with alert status
        """
        try:
            # Get latest health score from metrics
            query = {
                "query": {
                    "match": {"metric_type": "health_score"}
                },
                "size": 1,
                "sort": [{"timestamp": {"order": "desc"}}]
            }

            results = self.es.search(query=query, index="soar-metrics", size=1)
            hits = results.get("hits", {}).get("hits", [])

            if not hits:
                return {"status": "no_data", "message": "No health score data available"}

            health_score = hits[0].get("_source", {}).get("score", 0)
            threshold = self.thresholds["health_score"]

            if health_score < threshold:
                alert = {
                    "status": "alert",
                    "metric": "health_score",
                    "value": health_score,
                    "threshold": threshold,
                    "message": f"Health score below threshold: {health_score} < {threshold}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self._send_alert(alert)
                return alert

            return {
                "status": "ok",
                "metric": "health_score",
                "value": health_score,
                "threshold": threshold
            }

        except Exception as e:
            logger.error(f"Error checking health score: {e}")
            return {"status": "error", "message": str(e)}

    def check_all_thresholds(self, hours: int = 1) -> Dict[str, Any]:
        """
        Check all KPI thresholds.
        
        Args:
            hours: Time period in hours
            
        Returns:
            Dict with all check results
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "mttr": self.check_mttr_threshold(hours),
                "service_health": self.check_service_health(hours),
                "health_score": self.check_health_score()
            }
        }

        # Overall status
        all_ok = all(
            check.get("status") in ("ok", "no_data")
            for check in results["checks"].values()
        )
        results["overall_status"] = "ok" if all_ok else "alert"

        return results

    def _send_alert(self, alert: Dict[str, Any]) -> None:
        """
        Send alert via webhook if configured.
        
        Args:
            alert: Alert data
        """
        if not self.webhook_url:
            logger.warning(f"Alert webhook not configured. Alert: {alert}")
            return

        try:
            import requests
            requests.post(self.webhook_url, json=alert, timeout=10)
            logger.info(f"Alert sent: {alert.get('message')}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
