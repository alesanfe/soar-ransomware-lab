
#!/usr/bin/env python3
"""
SOAR Ransomware Lab - KPI Calculator
Calculates MTTR metrics from workflow execution logs
"""
import re
import csv
import statistics
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/kpi_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
LOG_PATH = Path('logs/notify.log')
RESULTS_PATH = Path('results')
RESULTS_PATH.mkdir(parents=True, exist_ok=True)

def validate_log_file() -> Path:
    """Validate log file existence and readability"""
    try:
        if not LOG_PATH.exists():
            logger.error(f"Log file not found: {LOG_PATH}")
            raise FileNotFoundError(f"Log file not found: {LOG_PATH}")
        
        if not LOG_PATH.is_file():
            logger.error(f"Log path is not a file: {LOG_PATH}")
            raise ValueError(f"Log path is not a file: {LOG_PATH}")
        
        # Test file readability
        with open(LOG_PATH, 'r') as f:
            f.readline()
        
        logger.info(f"Log file validated: {LOG_PATH}")
        return LOG_PATH
        
    except PermissionError:
        logger.error(f"Permission denied accessing log file: {LOG_PATH}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating log file: {e}")
        raise

def parse_log_file(log_file: Path) -> Dict[str, List[datetime]]:
    """Parse log file to extract execution timestamps"""
    logger.info(f"Parsing log file: {log_file}")
    
    alert_steps = defaultdict(list)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                m = re.match(r"\[(.*?)\]\sSTEP:\s(.*)", line)
                if m:
                    try:
                        ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                        step_name = m.group(2)
                        alert_steps[step_name].append(ts)
                    except ValueError as e:
                        logger.warning(f"Invalid timestamp format at line {line_num}: {e}")
                        continue
                else:
                    logger.debug(f"Line {line_num} doesn't match expected format: {line}")
        
        logger.info(f"Parsed {sum(len(times) for times in alert_steps.values())} log entries")
        return dict(alert_steps)
        
    except UnicodeDecodeError:
        logger.error(f"Unicode decode error in log file: {log_file}")
        raise
    except Exception as e:
        logger.error(f"Error parsing log file: {e}")
        raise

def calculate_execution_times(alert_steps: Dict[str, List[datetime]]) -> List[float]:
    """Calculate execution times from alert steps"""
    logger.info("Calculating execution times")
    
    alert_times = alert_steps.get('Alert received', [])
    containment_times = alert_steps.get('Containment executed', [])
    
    if not alert_times:
        logger.warning("No 'Alert received' steps found")
        return []
    
    if not containment_times:
        logger.warning("No 'Containment executed' steps found")
        return []
    
    # Pair up alerts with their corresponding containment actions
    min_pairs = min(len(alert_times), len(containment_times))
    execution_times = []
    
    for i in range(min_pairs):
        try:
            delta = (containment_times[i] - alert_times[i]).total_seconds()
            if delta > 0:  # Only include valid positive time differences
                execution_times.append(delta)
            else:
                logger.warning(f"Negative or zero execution time at index {i}: {delta}s")
        except Exception as e:
            logger.error(f"Error calculating execution time at index {i}: {e}")
            continue
    
    logger.info(f"Calculated {len(execution_times)} valid execution times")
    return execution_times

def calculate_metrics(execution_times: List[float]) -> Dict[str, Any]:
    """Calculate statistical metrics from execution times"""
    if not execution_times:
        logger.warning("No execution times provided")
        return {}
    
    try:
        # Calculate statistical metrics
        mean_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        
        # Calculate percentiles
        sorted_times = sorted(execution_times)
        n = len(sorted_times)
        p50_idx = int(n * 0.5)
        p90_idx = int(n * 0.9)
        
        p50 = sorted_times[p50_idx] if n > 0 else 0
        p90 = sorted_times[p90_idx] if n > 0 else 0
        
        # Standard deviation
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
        
        metrics = {
            'total_executions': len(execution_times),
            'mean': round(mean_time, 2),
            'median': round(median_time, 2),
            'p50': round(p50, 2),
            'p90': round(p90, 2),
            'min': round(min(execution_times), 2),
            'max': round(max(execution_times), 2),
            'std_dev': round(std_dev, 2)
        }
        
        logger.info(f"Calculated metrics: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise

def save_metrics(metrics: Dict[str, Any], output_file: Path) -> None:
    """Save metrics to CSV file"""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=metrics.keys())
            w.writeheader()
            w.writerow(metrics)
        
        logger.info(f"Metrics saved to {output_file}")
        
    except PermissionError:
        logger.error(f"Permission denied writing to {output_file}")
        raise
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")
        raise

def print_metrics_summary(metrics: Dict[str, Any]) -> None:
    """Print formatted metrics summary"""
    if not metrics:
        logger.warning("No metrics to display")
        return
    
    print(f'KPIs calculados en results/kpis.csv')
    print(f'  Total ejecuciones: {metrics["total_executions"]}')
    print(f'  MTTR (media): {metrics["mean"]}s')
    print(f'  p50: {metrics["p50"]}s')
    print(f'  p90: {metrics["p90"]}s')
    print(f'  Desviación estándar: {metrics["std_dev"]}s')
    
    # Check against thresholds
    p50 = metrics.get('p50', 0)
    p90 = metrics.get('p90', 0)
    
    if p50 <= 120:
        print(f'  ✓ p50 cumple umbral (≤120s)')
    else:
        print(f'  ✗ p50 excede umbral (>120s)')
    
    if p90 <= 180:
        print(f'  ✓ p90 cumple umbral (≤180s)')
    else:
        print(f'  ✗ p90 excede umbral (>180s)')

def main() -> None:
    """Main function to calculate KPIs"""
    try:
        logger.info("Starting KPI calculation")
        
        # Validate log file
        log_file = validate_log_file()
        
        # Parse log file
        alert_steps = parse_log_file(log_file)
        
        # Calculate execution times
        execution_times = calculate_execution_times(alert_steps)
        
        if execution_times:
            # Calculate metrics
            metrics = calculate_metrics(execution_times)
            
            # Save metrics
            output_file = RESULTS_PATH / 'kpis.csv'
            save_metrics(metrics, output_file)
            
            # Print summary
            print_metrics_summary(metrics)
            
            logger.info("KPI calculation completed successfully")
        else:
            logger.warning("No complete executions found in log")
            print('No se encontraron ejecuciones completas en el log.')
            print('Se requieren pares de "Alert received" y "Containment executed"')
            
    except Exception as e:
        logger.error(f"KPI calculation failed: {e}")
        print(f'Error: {e}')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
