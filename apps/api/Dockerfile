
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy package definition and source first for dependency resolution
COPY pyproject.toml .
COPY src ./src

# Install the package plus test dependencies (container is used for running tests)
RUN pip install --no-cache-dir .[test]

# Copy test suite (after install so test-only changes don't invalidate the package layer)
COPY tests ./tests

# Copy static API docs used by main.py root/static-docs handlers
COPY apps/api/api-docs.html ./api-docs.html
COPY apps/api/docs ./docs

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

# Run the application using the composition root factory
CMD ["uvicorn", "soar_lab.interfaces.api.composition:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
