
#!/usr/bin/env python3
import re, csv, statistics
from datetime import datetime
from pathlib import Path

log_path = Path('logs/notify.log')
results_path = Path('results')
results_path.mkdir(parents=True, exist_ok=True)

if not log_path.exists():
    print('No existe logs/notify.log')
    raise SystemExit(1)

steps = {}
for line in log_path.read_text().splitlines():
    m = re.match(r"\[(.*?)\]\sSTEP:\s(.*)", line)
    if m:
        ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        steps[m.group(2)] = ts

if 'Alert received' in steps and 'Containment executed' in steps:
    delta = (steps['Containment executed'] - steps['Alert received']).total_seconds()
    metrics = {
        'mean': round(delta, 2),
        'p50': round(delta, 2),
        'p90': round(delta, 2),
        'std_dev': 0.0
    }
    with open(results_path / 'kpis.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=metrics.keys())
        w.writeheader(); w.writerow(metrics)
    print('KPIs calculados en results/kpis.csv')
else:
    print('No se encontraron pasos requeridos en el log.')
