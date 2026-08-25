#!/usr/bin/env python3
"""
Patch cortexutils to read input from file when stdin is empty.

This script is injected into analyzer Docker images to fix the stdin issue
on Docker Desktop (WSL2). It monkey-patches the Worker class to read input
from input/input.json when stdin is empty.

This file is installed as a sitecustomize.py, which Python executes
automatically on startup (before any user script).
"""

import json
import os
import sys

# Find the cortexutils worker module
try:
    import cortexutils.worker as worker_module
except ImportError:
    # cortexutils not installed yet, nothing to patch
    sys.exit(0)

# Save the original __init__
_original_init = worker_module.Worker.__init__

def _patched_init(self, job_directory=None, secret_phrases=None):
    """Patched __init__ that reads input from file when stdin is empty."""
    # Check if stdin has data
    has_stdin = False
    try:
        if not sys.stdin.isatty():
            # Try to read a byte with a timeout
            import select
            r, _, _ = select.select([sys.stdin], [], [], 0.1)
            has_stdin = bool(r)
    except (OSError, ValueError):
        has_stdin = False
    
    if not has_stdin:
        # Read from input/input.json in the job directory
        # The job directory is passed as job_directory argument
        job_dir = job_directory or os.environ.get("CORTEX_JOB_DIR") or os.getcwd()
        
        # Try multiple locations
        for input_file in [
            os.path.join(job_dir, "input", "input.json"),
            os.path.join("/job", "input", "input.json"),
            "input/input.json",
        ]:
            if os.path.exists(input_file):
                with open(input_file) as f:
                    input_data = f.read()
                # Replace sys.stdin with a StringIO containing the data
                import io
                sys.stdin = io.StringIO(input_data)
                break
    
    # Call the original __init__
    _original_init(self, job_directory, secret_phrases)

# Apply the patch
worker_module.Worker.__init__ = _patched_init
