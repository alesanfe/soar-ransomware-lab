FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install system dependencies, Python dependencies, create directories, and setup user in single layer
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/results /app/backups \
    && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && rm -rf /var/lib/apt/lists/*
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request, sys; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "entrypoint:app", "--host", "0.0.0.0", "--port", "8000"]
