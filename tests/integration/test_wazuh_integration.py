#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Wazuh Integration Tests
Complete integration tests for Wazuh
"""

import os

import pytest
from soar_lab.infrastructure.external.integrations.wazuh_client import WazuhClient
from unittest.mock import Mock, patch


class TestWazuhIntegration:
    """Test Wazuh integration"""

    @pytest.fixture
    def wazuh_client(self):
        """Create Wazuh client for testing"""
        return WazuhClient(
            base_url=os.environ.get("WAZUH_API_URL", "http://localhost:55100"),
            username="wazuh-wui",
            password=os.environ.get("WAZUH_API_PASSWORD", ""),
            verify_ssl=False,
            token="test-token",
        )

    def test_connection_and_authentication(self, wazuh_client):
        """Test Wazuh connection and authentication"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"version": "4.4.0"}}
            )

            info = wazuh_client.get_api_info()
            assert info is not None, "Should connect to Wazuh"
            assert 'version' in info['data'], "Should return version info"

    def test_agent_list(self, wazuh_client):
        """Test agent listing"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "items": [
                            {"id": "000", "name": "wazuh-manager", "ip": "127.0.0.1", "status": "active"},
                            {"id": "001", "name": "agent-001", "ip": "192.168.1.100", "status": "active"}
                        ]
                    }
                }
            )

            agents = wazuh_client.list_agents()
            assert len(agents) > 0, "Should return agents"
            assert agents[0]['name'] == "wazuh-manager", "Should return manager agent"

    def test_agent_details(self, wazuh_client):
        """Test getting agent details"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "id": "001",
                        "name": "agent-001",
                        "ip": "192.168.1.100",
                        "status": "active",
                        "os": {"name": "Windows", "version": "10"}
                    }
                }
            )

            agent = wazuh_client.get_agent("001")
            assert agent['name'] == "agent-001", "Should return agent details"
            assert agent['status'] == "active", "Agent should be active"

    def test_active_response_command(self, wazuh_client):
        """Test active response command execution"""
        with patch.object(wazuh_client.session, 'post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Command sent successfully"}}
            )

            result = wazuh_client.run_active_response(
                agent_id="001",
                command="restart-wazuh"
            )
            assert result['data']['message'] == "Command sent successfully", \
                "Command should be sent successfully"

    def test_alert_retrieval(self, wazuh_client):
        """Test alert retrieval"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "items": [
                            {
                                "id": "1670000000",
                                "rule": {"level": 10, "description": "Ransomware activity"},
                                "agent": {"name": "agent-001", "id": "001"}
                            }
                        ]
                    }
                }
            )

            alerts = wazuh_client.get_alerts()
            assert len(alerts) > 0, "Should return alerts"
            assert alerts[0]['rule']['level'] == 10, "Alert should have level"

    def test_agent_restart(self, wazuh_client):
        """Test agent restart"""
        with patch.object(wazuh_client.session, 'put') as mock_put:
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Agent restarted"}}
            )

            result = wazuh_client.restart_agent("001")
            assert result['data']['message'] == "Agent restarted", "Agent should be restarted"

    def test_agent_isolation(self, wazuh_client):
        """Test agent isolation"""
        with patch.object(wazuh_client.session, 'put') as mock_put:
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Agent isolated"}}
            )

            result = wazuh_client.isolate_agent("001")
            assert result['data']['message'] == "Agent isolated", "Agent should be isolated"

    def test_syscheck_scan(self, wazuh_client):
        """Test syscheck scan trigger"""
        with patch.object(wazuh_client.session, 'put') as mock_put:
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Syscheck scan started"}}
            )

            result = wazuh_client.start_syscheck_scan("001")
            assert result['data']['message'] == "Syscheck scan started", \
                "Syscheck scan should be started"

    def test_agent_upgrade(self, wazuh_client):
        """Test agent upgrade"""
        with patch.object(wazuh_client.session, 'put') as mock_put:
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Agent upgrade started"}}
            )

            result = wazuh_client.upgrade_agent("001", "4.4.0")
            assert result['data']['message'] == "Agent upgrade started", \
                "Agent upgrade should be started"

    def test_group_assignment(self, wazuh_client):
        """Test group assignment to agent"""
        with patch.object(wazuh_client.session, 'put') as mock_put:
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {"data": {"message": "Group assigned"}}
            )

            result = wazuh_client.assign_group("001", "ransomware")
            assert result['data']['message'] == "Group assigned", "Group should be assigned"

    def test_file_integrity_monitoring(self, wazuh_client):
        """Test file integrity monitoring data"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "items": [
                            {
                                "path": "C:\\Windows\\System32\\malware.exe",
                                "event": "added",
                                "md5": "d41d8cd98f00b204e9800998ecf8427e"
                            }
                        ]
                    }
                }
            )

            fim_events = wazuh_client.get_fim_events("001")
            assert len(fim_events) > 0, "Should return FIM events"
            assert fim_events[0]['event'] == "added", "Should have event type"

    def test_vulnerability_detection(self, wazuh_client):
        """Test vulnerability detection"""
        with patch.object(wazuh_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "data": {
                        "items": [
                            {
                                "cve": "CVE-2021-34527",
                                "severity": "Critical",
                                "status": " vulnerable"
                            }
                        ]
                    }
                }
            )

            vulnerabilities = wazuh_client.get_vulnerabilities("001")
            assert len(vulnerabilities) > 0, "Should return vulnerabilities"
            assert vulnerabilities[0]['severity'] == "Critical", "Should have severity"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
