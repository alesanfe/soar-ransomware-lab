"""Log Parser - Infrastructure implementation for parsing execution logs.

This adapter encapsulates log parsing logic for MTTR calculation,
allowing the application layer to remain infrastructure-agnostic.
"""

import re
from collections import defaultdict
from datetime import UTC, datetime

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class ExecutionLogParser:
    """Infrastructure implementation of LogParser port for execution logs."""

    def parse(self, log_content: str) -> dict[str, list[datetime]]:
        """Parse execution logs to extract timestamps for MTTR calculation.

        Args:
            log_content: Log file content as string

        Returns:
            Dict mapping step names to list of timestamps
        """
        alert_steps = defaultdict(list)

        for line_num, line in enumerate(log_content.split("\n"), 1):
            line = line.strip()
            if not line:
                continue

            # Format 1 (original): [TIMESTAMP] STEP: name
            m = re.match(r"\[(.*?)\]\sSTEP:\s(.*)", line)
            # Format 2 (actual notify.log): [TIMESTAMP] TC-XX STEP N: description
            if not m:
                m = re.match(r"\[(.*?)\]\s+\S+\s+STEP\s+\d+:\s+(.*)", line)
            # Format 3: [TIMESTAMP] TC-XX === ... STARTED/COMPLETED/PASSED
            if not m:
                m2 = re.match(
                    r"\[(.*?)\]\s+\S+\s+=+\s+(TC-\d+.*?(?:STARTED|PASSED|FAILED))\s*=+", line
                )
                if m2:
                    m = m2

            if m:
                try:
                    ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                    step_name = m.group(2).strip()
                    alert_steps[step_name].append(ts)
                except ValueError as e:
                    logger.warning(f"Invalid timestamp format at line {line_num}: {e}")
                    continue

        logger.info(f"Parsed {sum(len(times) for times in alert_steps.values())} log entries")
        return dict(alert_steps)
