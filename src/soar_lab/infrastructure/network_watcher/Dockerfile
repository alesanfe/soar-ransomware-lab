FROM python:3.11-alpine
RUN apk add --no-cache socat && pip install --no-cache-dir docker==7.1.0
COPY _constants.py /app/_constants.py
COPY _handler.py /app/_handler.py
COPY network_watcher.py /app/network_watcher.py
WORKDIR /app
ENV PYTHONPATH=/app
CMD ["python", "-u", "/app/network_watcher.py"]
