#!/usr/bin/env python3
"""
Unit tests for in_memory_alert_repository.py
"""

import pytest

from soar_lab.infrastructure.in_memory_alert_repository import InMemoryAlertRepository


class TestInMemoryAlertRepository:
    """Test InMemoryAlertRepository infrastructure adapter"""

    def test_initialization(self):
        """Test successful initialization"""
        repo = InMemoryAlertRepository()
        
        assert repo._store == {}

    def test_store_alert(self):
        """Test storing an alert"""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open"
        }
        
        alert_id = repo.store(alert)
        
        assert alert_id == "alert-1"
        assert repo._store["alert-1"] == alert

    def test_store_alert_copy(self):
        """Test that stored alert is a copy, not reference"""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open"
        }
        
        repo.store(alert)
        alert["status"] = "closed"
        
        assert repo._store["alert-1"]["status"] == "open"

    def test_find_by_id_exists(self):
        """Test finding an alert by ID when it exists"""
        repo = InMemoryAlertRepository()
        alert = {
            "alert_id": "alert-1",
            "alert_type": "ransomware",
            "severity": "high",
            "status": "open"
        }
        repo.store(alert)
        
        found = repo.find_by_id("alert-1")
        
        assert found == alert

    def test_find_by_id_not_exists(self):
        """Test finding an alert by ID when it doesn't exist"""
        repo = InMemoryAlertRepository()
        
        found = repo.find_by_id("nonexistent")
        
        assert found is None

    def test_find_by_type(self):
        """Test finding alerts by type"""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "ransomware", "severity": "low"})
        repo.store({"alert_id": "alert-3", "alert_type": "phishing", "severity": "high"})
        
        alerts = repo.find_by_type("ransomware")
        
        assert len(alerts) == 2
        assert all(a["alert_type"] == "ransomware" for a in alerts)

    def test_find_by_type_no_matches(self):
        """Test finding alerts by type with no matches"""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        
        alerts = repo.find_by_type("phishing")
        
        assert len(alerts) == 0

    def test_find_by_severity(self):
        """Test finding alerts by severity"""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-3", "alert_type": "phishing", "severity": "low"})
        
        alerts = repo.find_by_severity("high")
        
        assert len(alerts) == 2
        assert all(a["severity"] == "high" for a in alerts)

    def test_find_by_severity_no_matches(self):
        """Test finding alerts by severity with no matches"""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        
        alerts = repo.find_by_severity("low")
        
        assert len(alerts) == 0

    def test_update_status_exists(self):
        """Test updating status of existing alert"""
        repo = InMemoryAlertRepository()
        alert = {"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high", "status": "open"}
        repo.store(alert)
        
        result = repo.update_status("alert-1", "closed")
        
        assert result == True
        assert repo._store["alert-1"]["status"] == "closed"

    def test_update_status_not_exists(self):
        """Test updating status of non-existent alert"""
        repo = InMemoryAlertRepository()
        
        result = repo.update_status("nonexistent", "closed")
        
        assert result == False

    def test_clear(self):
        """Test clearing all alerts"""
        repo = InMemoryAlertRepository()
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high"})
        repo.store({"alert_id": "alert-2", "alert_type": "phishing", "severity": "low"})
        
        repo.clear()
        
        assert repo._store == {}

    def test_multiple_operations(self):
        """Test multiple operations in sequence"""
        repo = InMemoryAlertRepository()
        
        # Store multiple alerts
        repo.store({"alert_id": "alert-1", "alert_type": "ransomware", "severity": "high", "status": "open"})
        repo.store({"alert_id": "alert-2", "alert_type": "phishing", "severity": "medium", "status": "open"})
        repo.store({"alert_id": "alert-3", "alert_type": "ransomware", "severity": "low", "status": "open"})
        
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
