
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching (build context = repo root)
COPY apps/api/requirements.txt .

# Copy application source code (build context must be repo root)
COPY src ./src
COPY pyproject.toml .
COPY tests ./tests
COPY apps/api/api-docs.html ./api-docs.html
COPY apps/api/docs ./docs

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install testing dependencies (container is used for running tests)
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov

# Create directories
RUN mkdir -p /app/results /app/backups

# Setup user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

ENV PYTHONPATH=/app/src

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "soar_lab.api:app", "--host", "0.0.0.0", "--port", "8000"]
