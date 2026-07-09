#!/usr/bin/env python3
"""
Unit tests for send_wazuh_alert module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.services.send_wazuh_alert import main


class TestMain:
    """Tests for main function."""

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'malicious', '--single'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_single_malicious_alert(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test main with single malicious alert."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_malicious.return_value = {"alert_id": "WAZ-001"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": True}
        mock_sender_instance.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            main()

        mock_sender_instance.send.assert_called_once()

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'benign', '--single'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_single_benign_alert(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test main with single benign alert."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_benign.return_value = {"alert_id": "WAZ-BEN-001"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": True}
        mock_sender_instance.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            main()

        mock_sender_instance.send.assert_called_once()

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'malicious', '--num-alerts', '2', '--delay', '0'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_multiple_alerts(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test main with multiple alerts."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_malicious.return_value = {"alert_id": "WAZ-001"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": True}
        mock_sender_instance.get_metrics.return_value = {"alerts_sent": 2, "alerts_failed": 0}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            main()

        assert mock_sender_instance.send.call_count == 2

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'malicious', '--single'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_send_failure(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test main when alert sending fails."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_malicious.return_value = {"alert_id": "WAZ-001"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": False, "error": "Connection failed"}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'malicious', '--single', '--workflow-id', 'wf-123'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_with_workflow_id(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test main with workflow ID (uses execution endpoint)."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_malicious.return_value = {"alert_id": "WAZ-001"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": True}
        mock_sender_instance.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            main()

        # Verify sender was initialized with execution URL
        mock_sender.assert_called_once()
        call_kwargs = mock_sender.call_args[1]
        assert "workflows/wf-123/execute" in call_kwargs['webhook_url']

    @patch('sys.argv', ['send_wazuh_alert', '--type', 'malicious', '--single'])
    @patch('soar_lab.infrastructure.http_alert_sender.HTTPAlertSender')
    @patch('soar_lab.domain.alert_generator.AlertGenerator')
    @patch('soar_lab.config.logging.get_logger')
    def test_main_wazuh_fields_added(self, mock_get_logger, mock_alert_gen, mock_sender):
        """Test that Wazuh-specific fields are added to alert."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_alert_gen_instance = Mock()
        mock_alert_gen.return_value = mock_alert_gen_instance
        mock_alert_gen_instance.generate_malicious.return_value = {"alert_id": "WAZ-001", "src_ip": "192.168.1.100"}
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send.return_value = {"success": True}
        mock_sender_instance.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}

        with patch.dict('os.environ', {'BASE_DIR': str(REPO_ROOT), 'WAZUH_WEBHOOK_URL': 'http://localhost:5001/api/v1/hooks/webhook', 'SIEM_WEBHOOK_TOKEN': 'test-token'}):
            main()

        # Verify Wazuh fields were added
        sent_alert = mock_sender_instance.send.call_args[0][0]
        assert sent_alert["wazuh_agent_id"] == "001"
        assert sent_alert["wazuh_agent_name"] == "simulated-agent"
        assert sent_alert["wazuh_agent_ip"] == "192.168.1.100"
        assert sent_alert["source"] == "wazuh-siem"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
