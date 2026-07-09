#!/bin/bash
# Script to run e2e tests inside the Docker API container

TEST_PATH=$1

if [ -z "$TEST_PATH" ]; then
    echo "Usage: $0 <test_path>"
    echo "Example: $0 tests/e2e/TC-01/test_malicious.py"
    exit 1
fi

# Copy the test file to the container
docker cp "$TEST_PATH" soar_api:/app/test.py

# Run the test
docker exec soar_api python /app/test.py
