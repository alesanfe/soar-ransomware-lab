"""Pytest Output Parser - Infrastructure implementation for test result parsing.

This adapter encapsulates pytest output parsing logic,
allowing the application layer to remain infrastructure-agnostic.
"""

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class PytestOutputParser:
    """Infrastructure implementation of TestResultParserInterface for pytest output."""

    def parse(self, output: str) -> dict:
        """
        Parse test results from pytest output.

        Args:
            output: Pytest output string

        Returns:
            Dict with passed, failed, skipped, and coverage
        """
        passed = failed = skipped = 0
        coverage = 0.0

        for line in output.split('\n'):
            # Parse test summary line
            if 'passed' in line or 'failed' in line or 'skipped' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i < len(parts) - 1:
                        next_word = parts[i + 1].replace(',', '').replace(':', '')
                        if next_word == 'passed':
                            passed = int(part)
                        elif next_word == 'failed':
                            failed = int(part)
                        elif next_word == 'skipped':
                            skipped = int(part)
            # Parse coverage from TOTAL line
            elif line.startswith('TOTAL') and '%' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage = float(parts[-1].replace('%', ''))

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "coverage": coverage
        }
