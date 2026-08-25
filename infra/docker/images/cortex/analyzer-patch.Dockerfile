# Patch each analyzer image to fix stdin issue on Docker Desktop (WSL2)
# Cortex mounts the job directory at /job, but the analyzer runs with
# job_directory=None, so it can't find input/input.json and falls back to
# stdin which is empty. This patch wraps the stdin read with a fallback.

ARG ANALYZER_IMAGE
FROM ${ANALYZER_IMAGE}

COPY patch_worker.py /tmp/patch_worker.py
RUN python /tmp/patch_worker.py && rm /tmp/patch_worker.py
