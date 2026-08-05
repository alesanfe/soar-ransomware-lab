FROM python:3.11-alpine
RUN apk add --no-cache socat && pip install --no-cache-dir docker==7.1.0
COPY network_watcher.py /app/network_watcher.py
CMD ["python", "-u", "/app/network_watcher.py"]
