#!/usr/bin/env python3
"""
Tests to increase code coverage for SOAR Ransomware Lab
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.tfm_data_enhancer import TFMDataEnhancer
from scripts.tfm_data_viewer import TFMDataViewer
from scripts.calc_kpis import validate_log_file, parse_log_file, calculate_execution_times, calculate_metrics, save_metrics, print_metrics_summary
import scripts.generate_iocs as generate_iocs
import scripts.generate_secrets as generate_secrets
import config.schemas as schemas
from config.settings import Settings

class TestTFMDataEnhancerCoverage(unittest.TestCase):
    def setUp(self):
        self.enhancer = TFMDataEnhancer()

    @patch('scripts.tfm_data_enhancer.SIEMSimulator')
    @patch('time.sleep', return_value=None)
    def test_send_test_alerts(self, mock_sleep, mock_siem):
        mock_instance = mock_siem.return_value
        # Mock generate_test_alert instead of relying on SIEMSimulator real code during mock
        mock_instance.generate_test_alert.return_value = {'alert_id': 'TEST-001'}
        
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_instance.send_alert.return_value = mock_response
        
        results = self.enhancer.send_test_alerts(num_alerts=2)
        self.assertEqual(results['alerts_sent'], 2)
        self.assertEqual(mock_instance.send_alert.call_count, 2)

    @patch('scripts.calc_kpis.main')
    def test_calculate_enhanced_kpis(self, mock_calc_main):
        # Ensure results directory exists for the test
        self.enhancer.results_dir.mkdir(parents=True, exist_ok=True)
        self.enhancer.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy log file to avoid UnicodeDecodeError in parse_log_file
        # though we're mocking calc_kpis_main, it seems calculate_enhanced_kpis 
        # calls it directly which might trigger the validation.
        log_file = Path('logs/notify.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("[2024-01-01 12:00:00] STEP: Alert received\n")
            f.write("[2024-01-01 12:05:00] STEP: Containment executed\n")

        kpi_file = self.enhancer.results_dir / "kpis.csv"
        with open(kpi_file, 'w', encoding='utf-8') as f:
            f.write("metric,value\nmean,100\n")
            
        kpis = self.enhancer.calculate_enhanced_kpis()
        self.assertTrue(kpis['success'])
        self.assertIn('kpis', kpis)
        
        # Cleanup
        if kpi_file.exists():
            kpi_file.unlink()

    def test_calculate_additional_metrics(self):
        report = {
            'test_scenarios': {
                'scenarios': {
                    's1': {'success': True, 'duration': 10}
                }
            },
            'alert_simulation': {
                'alerts_sent': 5,
                'alerts_failed': 0
            },
            'kpis': {
                'kpis': {'efficiency_gain': 90}
            }
        }
        enhanced = self.enhancer.calculate_additional_metrics(report)
        self.assertEqual(enhanced['scenario_success_rate'], 100)
        self.assertEqual(enhanced['alert_success_rate'], 100)
        self.assertEqual(enhanced['efficiency_gain'], 90)

    def test_get_manual_baseline(self):
        baseline = self.enhancer.get_manual_baseline()
        self.assertEqual(baseline['total_time_manual'], 480.0)

    def test_generate_execution_summary(self):
        report = {
            'test_scenarios': {'scenarios': {'s1': {'success': True}}},
            'alert_simulation': {'alerts_sent': 5, 'alerts_failed': 0},
            'kpis': {'success': True},
            'system_status': {'services': {'s1': {'running': True}}}
        }
        summary = self.enhancer.generate_execution_summary(report)
        self.assertEqual(summary['scenarios_executed'], 1)
        self.assertEqual(summary['alerts_sent'], 5)
        self.assertTrue(summary['kpis_calculated'])

    @patch('subprocess.run')
    def test_run_test_scenarios(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        results = self.enhancer.run_test_scenarios()
        self.assertIn('scenarios', results)
        self.assertTrue(mock_run.called)

    @patch.object(TFMDataEnhancer, 'generate_comprehensive_report')
    @patch.object(TFMDataEnhancer, 'prepare_viewer_data')
    @patch('builtins.open', new_callable=mock_open)
    def test_run_complete_data_generation(self, mock_file, mock_prep, mock_gen):
        mock_gen.return_value = {'report_file': 'test.json'}
        mock_prep.return_value = {'metrics': {}}
        
        result = self.enhancer.run_complete_data_generation()
        self.assertTrue(result['success'])
        self.assertTrue(mock_file.called)

    def test_get_system_status(self):
        with patch('socket.socket.connect_ex', return_value=0):
            status = self.enhancer.get_system_status()
            self.assertIn('services', status)
            self.assertTrue(status['services']['thehive']['running'])

    @patch('builtins.open', new_callable=mock_open)
    def test_save_results(self, mock_file):
        data = {'test': 1}
        self.enhancer.save_results(data, Path('test.json'))
        mock_file.assert_called_with(Path('test.json'), 'w')

    @patch('scripts.tfm_data_enhancer.TFMDataEnhancer.run_complete_data_generation')
    @patch('sys.argv', ['tfm_data_enhancer.py', '--complete'])
    def test_enhancer_main(self, mock_run):
        from scripts.tfm_data_enhancer import main
        mock_run.return_value = {'duration': 1.0}
        main()
        self.assertTrue(mock_run.called)

    @patch('scripts.tfm_data_enhancer.SIEMSimulator')
    @patch('scripts.tfm_data_enhancer.TFMDataEnhancer.run_test_scenarios')
    @patch('scripts.tfm_data_enhancer.TFMDataEnhancer.send_test_alerts')
    @patch('scripts.tfm_data_enhancer.TFMDataEnhancer.calculate_enhanced_kpis')
    @patch('scripts.tfm_data_enhancer.TFMDataEnhancer.get_system_status')
    @patch('builtins.open', new_callable=mock_open)
    def test_generate_comprehensive_report(self, mock_file, mock_status, mock_kpis, mock_alerts, mock_scenarios, mock_siem):
        mock_status.return_value = {'services': {}}
        mock_kpis.return_value = {'success': True, 'kpis': {}}
        mock_alerts.return_value = {'alerts_sent': 5}
        mock_scenarios.return_value = {'scenarios': {}}
        
        report = self.enhancer.generate_comprehensive_report()
        self.assertIn('report_metadata', report)
        self.assertTrue(mock_file.called)

class TestTFMDataViewerCoverage(unittest.TestCase):
    def setUp(self):
        self.viewer = TFMDataViewer()

    def test_clear_cache(self):
        self.viewer._cache = {'test': 1}
        self.viewer.clear_cache()
        self.assertEqual(self.viewer._cache, {})

    def test_calculate_mttr_metrics(self):
        # Mocking parse_log_file indirectly by setting cache or mocking it
        with patch.object(self.viewer, 'parse_log_file') as mock_parse:
            # Provide enough entries to avoid "list index out of range"
            mock_parse.return_value = {
                'total_entries': 10,
                'entries': [
                    {'raw': '[2024-01-01 12:00:00] STEP: Alert received'},
                    {'raw': '[2024-01-01 12:00:10] STEP: Containment executed'},
                    {'raw': '[2024-01-01 12:01:00] STEP: Alert received'},
                    {'raw': '[2024-01-01 12:01:20] STEP: Containment executed'}
                ]
            }
            metrics = self.viewer.calculate_mttr_metrics()
            # The code seems to return soar_mttr_avg, soar_mttr_p50 etc.
            # but I saw 'mean_soaR' in the error output
            # Actually let me re-check the error output:
            # 'mean_soaR': 33.0, 'p50_soaR': 33.0, 'p90_soaR': 33.0
            self.assertIn('mean_soaR', metrics)

    def test_calculate_success_rates(self):
        # Mocking test_report_file reading
        with patch.object(self.viewer, 'test_report_file') as mock_file:
            mock_file.exists.return_value = True
            with patch('builtins.open', mock_open(read_data='Success Rate: 100%\nTotal Tests: 10\nSuccessful: 10\n')):
                metrics = self.viewer.calculate_success_rates()
                self.assertIn('success_rate_soaR', metrics)
                self.assertEqual(metrics['success_rate_soaR'], 100.0)

    def test_get_manual_baseline_data(self):
        data = self.viewer.get_manual_baseline_data()
        self.assertEqual(data['p30_manual'], 300)

    @patch('builtins.print')
    def test_display_placeholder_status(self, mock_print):
        with patch.object(self.viewer, 'extract_placeholders') as mock_extract:
            mock_extract.return_value = {'P1': {'description': 'Desc'}}
            # Mock metrics to avoid recursive failures
            with patch.object(self.viewer, 'calculate_mttr_metrics', return_value={}):
                with patch.object(self.viewer, 'calculate_success_rates', return_value={}):
                    with patch.object(self.viewer, 'calculate_cost_metrics', return_value={}):
                        self.viewer.display_placeholder_status()
                        self.assertTrue(mock_print.called)

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_export_data_json(self, mock_file, mock_json_dump):
        with patch.object(self.viewer, 'calculate_all_metrics') as mock_metrics:
            mock_metrics.return_value = {'m': 1}
            self.viewer.export_data_json('test_export.json')
            # Check if open was called with the right path
            mock_file.assert_called()

    @patch('builtins.print')
    def test_display_all_available_data(self, mock_print):
        with patch.object(self.viewer, 'calculate_all_metrics') as mock_metrics:
            mock_metrics.return_value = {'metric': 100}
            self.viewer.display_all_available_data()
            self.assertTrue(mock_print.called)

    def test_extract_placeholders(self):
        # Mock file reading of TFM file
        # Pattern is {variable: description - reference}
        # Use patch.object on Path class instead of instance if instance is read-only
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='- [ ] {P1: Desc - Ref}\n- [x] {P2: Done}\n')):
                placeholders = self.viewer.extract_placeholders()
                self.assertIn('P1', placeholders)
                self.assertIn('P2', placeholders)

    def test_parse_log_file(self):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='INFO - Log entry 1\nERROR - Log entry 2\n')):
                logs = self.viewer.parse_log_file(Path('dummy.log'))
                self.assertEqual(logs['total_entries'], 2)
                self.assertEqual(logs['info_count'], 1)
                self.assertEqual(logs['error_count'], 1)

    def test_parse_results_file_csv(self):
        csv_data = "col1,col2\nval1,val2\n"
        with patch('pathlib.Path.exists', return_value=True):
             with patch.object(Path, 'suffix', '.csv'):
                with patch('builtins.open', mock_open(read_data=csv_data)):
                    results = self.viewer.parse_results_file(Path('dummy.csv'))
                    self.assertEqual(results['total_records'], 1)
                    self.assertEqual(results['headers'], ['col1', 'col2'])

    @patch('scripts.tfm_data_viewer.TFMDataViewer.display_placeholder_status')
    @patch('sys.argv', ['tfm_data_viewer.py', '--status'])
    def test_viewer_main(self, mock_status):
        from scripts.tfm_data_viewer import main
        main()
        self.assertTrue(mock_status.called)

    def test_watch_data_changes(self):
        # Test watch_data_changes with KeyboardInterrupt
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            with patch.object(self.viewer, 'calculate_all_metrics', return_value={'m': 1}):
                self.viewer.watch_data_changes(interval=1)
                # Should not raise exception but print monitoring stopped

class TestCalcKPIsCoverage(unittest.TestCase):
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    def test_validate_log_file_success(self, mock_isfile, mock_exists):
        self.assertTrue(validate_log_file())

    def test_calculate_metrics_empty(self):
        metrics = calculate_metrics([])
        self.assertEqual(metrics['total_executions'], 0)
        self.assertEqual(metrics['mean'], 0)

    def test_calculate_metrics_values(self):
        metrics = calculate_metrics([10, 20, 30])
        self.assertEqual(metrics['total_executions'], 3)
        self.assertEqual(metrics['mean'], 20)
        self.assertEqual(metrics['p90'], 20) # 10*0.9=9. sorted[9-1]=sorted[1]=20

    @patch('builtins.print')
    def test_print_metrics_summary(self, mock_print):
        metrics = {
            'total_executions': 5,
            'mean': 10.5,
            'min': 5,
            'max': 20,
            'p50': 10,
            'p90': 18,
            'std_dev': 2.0
        }
        print_metrics_summary(metrics)
        self.assertTrue(mock_print.called)

class TestSchemasCoverage(unittest.TestCase):
    def test_is_valid_sha256(self):
        valid = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertTrue(schemas.is_valid_sha256(valid))
        self.assertFalse(schemas.is_valid_sha256("invalid"))
        self.assertFalse(schemas.is_valid_sha256(None))

    def test_is_valid_ip_address(self):
        self.assertTrue(schemas.is_valid_ip_address("192.168.1.1"))
        self.assertFalse(schemas.is_valid_ip_address("999.999.999.999"))
        self.assertFalse(schemas.is_valid_ip_address("not-an-ip"))

    def test_is_valid_alert_id(self):
        # Current implementation in schemas.py uses ALERT-\d{10}-\d{4}
        # ALERT-timestamp-sequence
        self.assertTrue(schemas.is_valid_alert_id("ALERT-1234567890-1234"))
        self.assertFalse(schemas.is_valid_alert_id("INVALID"))

    def test_validate_alert_data(self):
        # RansomwareAlert expects src_ip as IPv4Address object or string that can be parsed
        # and detection_time as datetime object
        # severity must be '0', '1', '2' or '3' (as strings because of str, Enum)
        valid_alert = {
            'alert_id': "ALERT-1234567890-1234",
            'hostname': 'WIN-001',
            'src_ip': '192.168.1.100',
            'hash': {'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
            'severity': '1',
            'source': 'SIEM',
            'detection_time': datetime.now(),
            'event_type': 'ransomware_detection',
            'description': 'Test',
            'affected_files': [],
            'mitre_tactics': [],
            'mitre_techniques': [],
            'network_events': []
        }
        is_valid, errors = schemas.validate_alert_data(valid_alert)
        self.assertTrue(is_valid, f"Validation failed with: {errors}")
        self.assertEqual(len(errors), 0)
        
        invalid_alert = valid_alert.copy()
        invalid_alert['severity'] = 'invalid'
        is_valid, errors = schemas.validate_alert_data(invalid_alert)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    def test_file_hash_model(self):
        valid_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        fh = schemas.FileHash(sha256=valid_hash)
        self.assertEqual(fh.sha256, valid_hash)
        
        with self.assertRaises(ValueError):
            schemas.FileHash(sha256="short")

class TestScriptsCoverage(unittest.TestCase):
    def test_generate_iocs_basic(self):
        h = generate_iocs.generate_malicious_hash(seed="test")
        self.assertEqual(len(h), 64)
        
        ips = generate_iocs.generate_ip_addresses(count=2)
        self.assertEqual(len(ips), 2)
        
        urls = generate_iocs.generate_urls(count=1)
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].startswith('http'))

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_create_ioc_package(self, mock_json, mock_file):
        generate_iocs.create_ioc_package("test.json", count=1)
        mock_file.assert_called_with("test.json", 'w')
        self.assertTrue(mock_json.called)

    def test_generate_secrets_basic(self):
        p = generate_secrets.generate_password(length=12)
        self.assertEqual(len(p), 12)
        
        k = generate_secrets.generate_api_key(length=32)
        self.assertEqual(len(k), 32)
        
        t = generate_secrets.generate_token(length=10)
        self.assertEqual(len(t), 10)

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_generate_all_secrets(self, mock_json, mock_file):
        generate_secrets.generate_all_secrets("test.json")
        mock_file.assert_called_with("test.json", 'w')
        self.assertTrue(mock_json.called)

class TestSettingsCoverage(unittest.TestCase):
    @patch.dict(os.environ, {"THEHIVE_HTTP_PORT": "1234"})
    def test_settings_load_env(self):
        s = Settings()
        self.assertEqual(s.get('thehive_port'), 1234)

    def test_settings_get_set(self):
        s = Settings()
        s.set('custom_key', 'value')
        self.assertEqual(s.get('custom_key'), 'value')
        self.assertEqual(s.get('non_existent', 'default'), 'default')

    def test_get_service_urls(self):
        s = Settings()
        s.set('enable_tls', False)
        s.set('thehive_port', 9000)
        urls = s.get_service_urls()
        self.assertEqual(urls['thehive'], "http://localhost:9000")

    def test_validate_settings(self):
        s = Settings()
        # Ensure required keys are set
        required_keys = ['elastic_password', 'thehive_secret', 'thehive_api_key', 
                         'cortex_secret', 'cortex_api_key', 'siem_webhook_token']
        for key in required_keys:
            s.set(key, 'test-value')
        self.assertTrue(s.validate())
        
        s.set('elastic_password', '')
        self.assertFalse(s.validate())

if __name__ == '__main__':
    unittest.main()
