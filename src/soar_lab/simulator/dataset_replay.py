"""Dataset replay — replay recorded alert datasets through the pipeline.

Loads alert datasets (``JSONL`` or ``JSON``) and replays them through an
injectable sender, so the same dataset produces comparable KPI runs —
the "benchmark mode" needed for reproducible SOAR experiments.
"""

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from soar_lab.config.logging import get_logger

__all__ = ["load_dataset", "replay_dataset"]

logger = get_logger(__name__)


def load_dataset(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield alert dicts from a dataset file.

    Supported formats:

    - ``.jsonl`` / ``.ndjson``: one JSON object per line (blank lines and
      ``#`` comments ignored).
    - ``.json``: a JSON array of objects, or an object with an ``alerts``
      (or ``events``) list.

    Args:
        path: Dataset file path.

    Yields:
        dict: Each alert/event, passed through unchanged.

    Raises:
        ValueError: On unsupported extension, malformed JSON, or entries
            that are not objects.
        FileNotFoundError: If the dataset does not exist.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()
    if suffix in (".jsonl", ".ndjson"):
        yield from _iter_jsonl(path)
        return
    if suffix == ".json":
        yield from _iter_json(path)
        return

    raise ValueError(f"Unsupported dataset format '{suffix}' (use .jsonl, .ndjson or .json)")


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSONL: {exc}") from exc
            if not isinstance(entry, dict):
                raise ValueError(f"{path}:{lineno}: entry is not a JSON object")
            yield entry


def _iter_json(path: Path) -> Iterator[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if isinstance(payload, dict):
        payload = payload.get("alerts", payload.get("events", []))
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON array or object with 'alerts'")
    for i, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry #{i} is not a JSON object")
        yield entry


def replay_dataset(
    alerts: Iterator[dict[str, Any]],
    send: Callable[[dict[str, Any]], bool],
    delay: float = 0.0,
    limit: int | None = None,
    on_result: Callable[[int, dict[str, Any], bool], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    tag: str | None = None,
) -> dict[str, Any]:
    """Replay alerts through a sender callable.

    Args:
        alerts: Iterator of alert dicts (from :func:`load_dataset`).
        send: Callable ``(alert) -> bool`` returning True on success.
        delay: Seconds between sends.
        limit: Optional cap on alerts replayed.
        on_result: Optional callback ``(index, alert, ok)`` per alert.
        sleep: Sleep callable (injectable for tests).

    Returns:
        dict: ``total``, ``sent``, ``failed``, ``success_rate``.
    """
    sent = failed = 0
    entries = alerts if limit is None else _take(alerts, limit)
    last_index = -1

    for index, alert in enumerate(entries):
        last_index = index
        # F1: variant label for A/B experiment comparison — the tag is
        # stored with the alert so `experiment_compare` can split KPIs.
        if tag and isinstance(alert, dict):
            alert = alert | {"experiment_tag": tag}
        try:
            ok = send(alert)
        except Exception as exc:
            logger.warning("Replay send failed for entry %s: %s", index, exc)
            ok = False
        if ok:
            sent += 1
        else:
            failed += 1
        if on_result is not None:
            on_result(index, alert, ok)
        if delay > 0:
            sleep(delay)

    total = last_index + 1
    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "success_rate": round(100.0 * sent / total, 2) if total else 0.0,
    }


def _take(alerts: Iterator[dict[str, Any]], limit: int) -> Iterator[dict[str, Any]]:
    for i, alert in enumerate(alerts):
        if i >= max(0, limit):
            break
        yield alert
