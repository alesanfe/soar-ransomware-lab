#!/usr/bin/env python3
"""
Unit tests for send_to_both_workflows module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.scripts.send_to_both_workflows import (
    _load_env,
    generate_malicious_alert,
    generate_benign_alert,
    send_alert_to_workflow,
    main
)


class TestLoadEnv:
    """Tests for _load_env function."""

    def test_load_env_from_file(self, tmp_path):
        """Test loading environment variables from file."""
        env_file = tmp_path / ".env.full"
        env_file.write_text("KEY1=value1\nKEY2=value2\n# Comment\nKEY3=value3\n")

        with patch('soar_lab.services.send_to_both_workflows.ENV_FULL', env_file):
            result = _load_env()

        assert result == {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3"
        }

    def test_load_env_empty_file(self, tmp_path):
        """Test loading from empty file."""
        env_file = tmp_path / ".env.full"
        env_file.write_text("")

        with patch('soar_lab.services.send_to_both_workflows.ENV_FULL', env_file):
            result = _load_env()

        assert result == {}

    def test_load_env_file_not_exists(self):
        """Test loading when file does not exist."""
        with patch('soar_lab.services.send_to_both_workflows.ENV_FULL', Path("/nonexistent/.env.full")):
            result = _load_env()

        assert result == {}

    def test_load_env_with_equals_in_value(self, tmp_path):
        """Test loading environment variables with equals sign in value."""
        env_file = tmp_path / ".env.full"
        env_file.write_text("KEY1=value=with=equals\n")

        with patch('soar_lab.services.send_to_both_workflows.ENV_FULL', env_file):
            result = _load_env()

        assert result == {"KEY1": "value=with=equals"}


class TestGenerateMaliciousAlert:
    """Tests for generate_malicious_alert function."""

    def test_generate_malicious_alert_simulated(self):
        """Test generating malicious alert for simulated workflow."""
        alert = generate_malicious_alert("simulated")

        assert alert["alert_type"] == "ransomware"
        assert alert["hostname"] == "WIN-SIM-001"
        assert alert["src_ip"] == "192.168.1.100"
        assert alert["severity"] == 2
        assert alert["process_name"] == "malware.exe"
        assert alert["hash"] == "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba"
        assert alert["mitre_techniques"] == ["T1486"]
        assert alert["source"] == "simulated-siem"
        assert alert["alert_id"].startswith("SIM-")
        assert "detection_time" in alert

    def test_generate_malicious_alert_wazuh(self):
        """Test generating malicious alert for Wazuh workflow."""
        alert = generate_malicious_alert("wazuh")

        assert alert["alert_type"] == "ransomware"
        assert alert["hostname"] == "WIN-WAZ-001"
        assert alert["src_ip"] == "192.168.1.101"
        assert alert["severity"] == 2
        assert alert["process_name"] == "malware.exe"
        assert alert["hash"] == "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba"
        assert alert["mitre_techniques"] == ["T1486"]
        assert alert["source"] == "wazuh-siem"
        assert alert["alert_id"].startswith("WAZ-")
        assert alert["wazuh_agent_id"] == "001"
        assert alert["wazuh_agent_name"] == "simulated-agent"
        assert alert["wazuh_agent_ip"] == "192.168.1.101"
        assert "detection_time" in alert


class TestGenerateBenignAlert:
    """Tests for generate_benign_alert function."""

    def test_generate_benign_alert_simulated(self):
        """Test generating benign alert for simulated workflow."""
        alert = generate_benign_alert("simulated")

        assert alert["alert_type"] == "file_access"
        assert alert["hostname"] == "WIN-SIM-002"
        assert alert["src_ip"] == "192.168.1.102"
        assert alert["severity"] == 1
        assert alert["process_name"] == "notepad.exe"
        assert alert["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
        assert alert["mitre_techniques"] == []
        assert alert["source"] == "simulated-siem"
        assert alert["alert_id"].startswith("SIM-BEN-")
        assert "detection_time" in alert

    def test_generate_benign_alert_wazuh(self):
        """Test generating benign alert for Wazuh workflow."""
        alert = generate_benign_alert("wazuh")

        assert alert["alert_type"] == "file_access"
        assert alert["hostname"] == "WIN-WAZ-002"
        assert alert["src_ip"] == "192.168.1.102"
        assert alert["severity"] == 1
        assert alert["process_name"] == "notepad.exe"
        assert alert["hash"] == "d41d8cd98f00b204e9800998ecf8427e"
        assert alert["mitre_techniques"] == []
        assert alert["source"] == "wazuh-siem"
        assert alert["alert_id"].startswith("WAZ-BEN-")
        assert alert["wazuh_agent_id"] == "002"
        assert alert["wazuh_agent_name"] == "benign-agent"
        assert alert["wazuh_agent_ip"] == "192.168.1.102"
        assert "detection_time" in alert


class TestSendAlertToWorkflow:
    """Tests for send_alert_to_workflow function."""

    def test_send_alert_to_workflow_success(self):
        """Test successful alert sending to workflow."""
        mock_shuffle_client = Mock()
        mock_shuffle_client.send_webhook.return_value = {
            "success": True,
            "execution_id": "exec-123"
        }

        payload = {"alert_id": "TEST-001"}
        result = send_alert_to_workflow("webhook-123", payload, mock_shuffle_client)

        assert result == "exec-123"
        mock_shuffle_client.send_webhook.assert_called_once_with("webhook-123", payload)

    def test_send_alert_to_workflow_failure(self):
        """Test alert sending failure."""
        mock_shuffle_client = Mock()
        mock_shuffle_client.send_webhook.return_value = {
            "success": False,
            "error": "Invalid webhook"
        }

        payload = {"alert_id": "TEST-001"}

        with pytest.raises(Exception, match="Shuffle did not accept alert"):
            send_alert_to_workflow("webhook-123", payload, mock_shuffle_client)

    def test_send_alert_to_workflow_no_execution_id(self):
        """Test alert sending when execution_id is not in response."""
        mock_shuffle_client = Mock()
        mock_shuffle_client.send_webhook.return_value = {
            "success": True
        }

        payload = {"alert_id": "TEST-001"}
        result = send_alert_to_workflow("webhook-123", payload, mock_shuffle_client)

        assert result == ""


class TestMain:
    """Tests for main function."""

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'malicious', '--single'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_single_malicious_alert(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main with single malicious alert."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_abc123"}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_def456"}'
        mock_send_alert.return_value = "exec-123"

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': 'test-key'}):
            main()

        assert mock_send_alert.call_count == 2

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'benign', '--single'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_single_benign_alert(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main with single benign alert."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_abc123"}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_def456"}'
        mock_send_alert.return_value = "exec-123"

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': 'test-key'}):
            main()

        assert mock_send_alert.call_count == 2

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'malicious', '--num-alerts', '2', '--delay', '0'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_multiple_alerts(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main with multiple alerts."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_abc123"}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_def456"}'
        mock_send_alert.return_value = "exec-123"

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': 'test-key'}):
            main()

        assert mock_send_alert.call_count == 4  # 2 alerts * 2 workflows

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'malicious', '--single'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_missing_simulated_webhook(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main when simulated webhook info is missing."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_def456"}'

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': 'test-key'}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'malicious', '--single'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_missing_wazuh_webhook(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main when Wazuh webhook info is missing."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_abc123"}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{}'

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': 'test-key'}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('sys.argv', ['send_to_both_workflows', '--type', 'malicious', '--single'])
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO')
    @patch('soar_lab.services.send_to_both_workflows.WEBHOOK_INFO_WAZUH')
    @patch('soar_lab.services.send_to_both_workflows.ShuffleClient')
    @patch('soar_lab.services.send_to_both_workflows.send_alert_to_workflow')
    def test_main_no_api_key(self, mock_send_alert, mock_shuffle_client, mock_wazuh_info, mock_sim_info):
        """Test main when no API key is provided."""
        mock_sim_info.exists.return_value = True
        mock_sim_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_abc123"}'
        mock_wazuh_info.exists.return_value = True
        mock_wazuh_info.read_text.return_value = '{"webhook_url": "http://shuffle/webhook_def456"}'
        mock_send_alert.return_value = "exec-123"

        with patch.dict('os.environ', {'SHUFFLE_URL': 'http://shuffle', 'SHUFFLE_API_KEY': ''}):
            main()

        # Verify ShuffleClient was initialized with placeholder API key
        mock_shuffle_client.assert_called_once()
        call_kwargs = mock_shuffle_client.call_args[1]
        assert call_kwargs['api_key'] == 'placeholder'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
