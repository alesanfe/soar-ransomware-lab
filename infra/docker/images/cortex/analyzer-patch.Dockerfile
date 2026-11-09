# checkov:skip=CKV_DOCKER_2: overlay image — inherits base analyzer healthcheck
# checkov:skip=CKV_DOCKER_3: overlay image — must keep the base analyzer's user
# Patch each analyzer image to fix stdin issue on Docker Desktop (WSL2)
# Cortex mounts the job directory at /job, but the analyzer runs with
# job_directory=None, so it can't find input/input.json and falls back to
# stdin which is empty. This patch wraps the stdin read with a fallback.

# Default pins one of the analyzer tags in patch_analyzers.py (all are
# version-tagged there); the script always overrides it via --build-arg.
ARG ANALYZER_IMAGE=ghcr.io/thehive-project/abuse_finder:3
# checkov:skip=CKV_DOCKER_7: base is parametrized; callers pass pinned tags (patch_analyzers.py list, ARG default pinned)
FROM ${ANALYZER_IMAGE}

COPY patch_worker.py /tmp/patch_worker.py
RUN python /tmp/patch_worker.py && rm /tmp/patch_worker.py
