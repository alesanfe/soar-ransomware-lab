
#!/usr/bin/env bash
# Simula notificación
echo "$(date '+%Y-%m-%d %H:%M:%S') STEP: Alert received" | tee -a logs/notify.log
