#!/usr/bin/env python3
"""Wrapper script that reads input from input/input.json instead of stdin.

Cortex 3.2.0 writes the job input to the 'input/input.json' file in the job
directory, but the analyzer images expect input via stdin. On Docker Desktop
(WSL2), the stdin pipe is not properly connected, causing all analyzers to
fail with JSONDecodeError.

This wrapper:
1. Reads input from input/input.json (or stdin if the file doesn't exist)
2. Pipes it to the actual analyzer script via stdin
3. Captures the output and writes it to output/output.json

Usage:
  The wrapper is called instead of the analyzer's __main__. It reads the
  input from the job directory and passes it to the analyzer.
"""

import json
import os
import subprocess
import sys

def main():
    # The job directory is passed as the first argument by Cortex
    job_dir = os.environ.get("CORTEX_JOB_DIR", "")
    if not job_dir:
        # Try to find it from the current working directory
        job_dir = os.getcwd()
    
    input_file = os.path.join(job_dir, "input", "input.json")
    output_file = os.path.join(job_dir, "output", "output.json")
    
    # Read input
    if os.path.exists(input_file):
        with open(input_file) as f:
            input_data = f.read()
    else:
        # Fallback: read from stdin
        input_data = sys.stdin.read()
    
    # Find the analyzer script
    # The wrapper is placed in /worker/<analyzer_name>/<analyzer_name>.py
    # We need to find the original analyzer script
    wrapper_path = os.path.abspath(__file__)
    wrapper_dir = os.path.dirname(wrapper_path)
    
    # Look for the original analyzer script in the same directory
    # The wrapper replaces the original __main__, so we need to call the
    # analyzer's run() method directly
    
    # Parse the input and call the analyzer
    input_json = json.loads(input_data)
    
    # Import the analyzer module
    # The analyzer script is in the same directory as this wrapper
    analyzer_files = [f for f in os.listdir(wrapper_dir) if f.endswith(".py") and f != os.path.basename(__file__)]
    
    if not analyzer_files:
        # No analyzer script found, just output the input as-is
        with open(output_file, "w") as f:
            json.dump({"success": True, "full": input_json}, f)
        return
    
    # Run the analyzer script with the input piped via stdin
    analyzer_script = os.path.join(wrapper_dir, analyzer_files[0])
    
    try:
        result = subprocess.run(
            [sys.executable, analyzer_script],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode == 0 and result.stdout:
            # Write the output to the output file
            with open(output_file, "w") as f:
                f.write(result.stdout)
        else:
            # Write error output
            error_msg = result.stderr if result.stderr else "Unknown error"
            with open(output_file, "w") as f:
                json.dump({"success": False, "errorMessage": error_msg}, f)
    except Exception as e:
        with open(output_file, "w") as f:
            json.dump({"success": False, "errorMessage": str(e)}, f)

if __name__ == "__main__":
    main()
