#!/usr/bin/env python3
"""Unit tests for in_memory_alert_repository.py."""

from soar_lab.infrastructure.in_memory_alert_repository import InMemoryAlertRepository


class TestInMemoryAlertRepository:
    """Test InMemoryAlertRepository infrastructure adapter."""

    def test_initialization(self):
        """Test successful initialization."""
        repo = InMemoryAlertRepository()

        assert repo._store == {}

    def test_store_alert(self):
        """Test storing an alert."""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open",
        }

        alert_id = repo.store(alert)

        assert alert_id == "alert-1"
        assert repo._store["alert-1"] == alert

    def test_store_alert_copy(self):
        """Test that stored alert is a copy, not reference."""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open",
        }

        repo.store(alert)
        alert["status"] = "closed"

        assert repo._store["alert-1"]["status"] == "open"

    def test_find_by_id_exists(self):
        """Test finding an alert by ID when it exists."""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open",
        }
        repo.store(alert)

        found = repo.find_by_id("alert-1")

        assert found == alert

    def test_find_by_id_not_exists(self):
        """Test finding an alert by ID when it doesn't exist."""
        repo = InMemoryAlertRepository()

        found = repo.find_by_id("nonexistent")

        assert found is None

    def test_find_by_type(self):
        """Test finding alerts by type."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "ransomware", "severity": "low"})
        repo.store({"alert_id": "alert-3", "alert_type": "phishing", "severity": "high"})

        alerts = repo.find_by_type("ransomware")

        assert len(alerts) == 2
        assert all(a["alert_type"] == "ransomware" for a in alerts)

    def test_find_by_type_no_matches(self):
        """Test finding alerts by type with no matches."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})

        alerts = repo.find_by_type("phishing")

        assert len(alerts) == 0

    def test_find_by_severity(self):
        """Test finding alerts by severity."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-3", "alert_type": "phishing", "severity": "low"})

        alerts = repo.find_by_severity("high")

        assert len(alerts) == 2
        assert all(a["severity"] == "high" for a in alerts)

    def test_find_by_severity_no_matches(self):
        """Test finding alerts by severity with no matches."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})

        alerts = repo.find_by_severity("low")

        assert len(alerts) == 0

    def test_update_status_exists(self):
        """Test updating status of existing alert."""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open",
        }
        repo.store(alert)

        result = repo.update_status("alert-1", "closed")

        assert result == True
        assert repo._store["alert-1"]["status"] == "closed"

    def test_update_status_not_exists(self):
        """Test updating status of non-existent alert."""
        repo = InMemoryAlertRepository()

        result = repo.update_status("nonexistent", "closed")

        assert result == False

    def test_clear(self):
        """Test clearing all alerts."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "phishing", "severity": "low"})

        repo.clear()

        assert repo._store == {}

    def test_multiple_operations(self):
        """Test multiple operations in sequence."""
        repo = InMemoryAlertRepository()

        # Store multiple alerts
        repo.store(
            {
                "alert_id": "alert-1",
                "alert_type": "ransomware",
                "severity": "high",
                "status": "open",
            }
        )
        repo.store(
            {
                "alert_id": "alert-2",
                "alert_type": "phishing",
                "severity": "medium",
                "status": "open",
            }
        )
        repo.store(
            {"alert_id": "alert-3", "alert_type": "ransomware", "severity": "low", "status": "open"}
        )

        # Find by type
        ransomware_alerts = repo.find_by_type("ransomware")
        assert len(ransomware_alerts) == 2

        # Find by severity
        high_alerts = repo.find_by_severity("high")
        assert len(high_alerts) == 1

        # Update status
        result = repo.update_status("alert-1", "closed")
        assert result == True

        # Verify update
        alert = repo.find_by_id("alert-1")
        assert alert["status"] == "closed"

        # Clear
        repo.clear()
        assert len(repo._store) == 0

    def test_get_test_results(self):
        """Test get_test_results returns empty list."""
        repo = InMemoryAlertRepository()

        result = repo.get_test_results(hours=24)

        assert result == []

    def test_get_alerts(self):
        """Test get_alerts returns all alerts."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "phishing", "severity": "low"})

        alerts = repo.get_alerts(hours=24)

        assert len(alerts) == 2

    def test_get_alerts_empty(self):
        """Test get_alerts returns empty list when no alerts."""
        repo = InMemoryAlertRepository()

        alerts = repo.get_alerts(hours=24)

        assert alerts == []

    def test_count_alerts(self):
        """Test count_alerts returns total number of alerts."""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "phishing", "severity": "low"})

        count = repo.count_alerts()

        assert count == 2

    def test_count_alerts_empty(self):
        """Test count_alerts returns 0 when no alerts."""
        repo = InMemoryAlertRepository()

        count = repo.count_alerts()

        assert count == 0

    def test_count_alerts_by_status(self):
        """Test count_alerts_by_status returns count of alerts with given
        status."""
        repo = InMemoryAlertRepository()
        repo.store(
            {
                "alert_id": "alert-1",
                "alert_type": "ransomware",
                "severity": "high",
                "status": "open",
            }
        )
        repo.store(
            {"alert_id": "alert-2", "alert_type": "phishing", "severity": "low", "status": "open"}
        )
        repo.store(
            {
                "alert_id": "alert-3",
                "alert_type": "ransomware",
                "severity": "high",
                "status": "closed",
            }
        )

        count = repo.count_alerts_by_status("open")

        assert count == 2

    def test_count_alerts_by_status_no_matches(self):
        """Test count_alerts_by_status returns 0 when no matches."""
        repo = InMemoryAlertRepository()
        repo.store(
            {
                "alert_id": "alert-1",
                "alert_type": "ransomware",
                "severity": "high",
                "status": "open",
            }
        )

        count = repo.count_alerts_by_status("closed")

        assert count == 0

    def test_count_cases(self):
        """Test count_cases returns 0 for in-memory repo."""
        repo = InMemoryAlertRepository()

        count = repo.count_cases()

        assert count == 0

    def test_count_cases_by_status(self):
        """Test count_cases_by_status returns 0 for in-memory repo."""
        repo = InMemoryAlertRepository()

        count = repo.count_cases_by_status("open")

        assert count == 0

    def test_count_backups_by_status(self):
        """Test count_backups_by_status returns 0 for in-memory repo."""
        repo = InMemoryAlertRepository()

        count = repo.count_backups_by_status("completed")

        assert count == 0

    def test_get_average_test_coverage(self):
        """Test get_average_test_coverage returns 0.0 for in-memory repo."""
        repo = InMemoryAlertRepository()

        coverage = repo.get_average_test_coverage(hours=24)

        assert coverage == 0.0
