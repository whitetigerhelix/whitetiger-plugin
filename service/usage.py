"""Usage tracking for LLM API credit consumption.

Logs each LLM call with token counts, estimated cost, and metadata.
Provides summary stats to help monitor how "hungry" the plugin is.

Data is stored in a local JSON-lines file (service/usage_log.jsonl).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Default log location (next to the service code)
DEFAULT_LOG_PATH = Path(__file__).parent / "usage_log.jsonl"


def log_usage(
    *,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    preset_id: str = "",
    bars: int = 0,
    cached: bool = False,
    duration_ms: int = 0,
    log_path: Path | None = None,
) -> dict:
    """Append a usage record to the log file. Returns the record."""
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "preset_id": preset_id,
        "bars": bars,
        "cached": cached,
        "duration_ms": duration_ms,
    }

    path = log_path or DEFAULT_LOG_PATH
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def get_usage_summary(log_path: Path | None = None) -> dict:
    """Read the usage log and return summary statistics."""
    path = log_path or DEFAULT_LOG_PATH

    if not path.exists():
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_estimated_cost_usd": 0.0,
            "cached_requests": 0,
            "by_model": {},
            "by_preset": {},
        }

    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    total_tokens = sum(r.get("total_tokens", 0) for r in records)
    total_cost = sum(r.get("estimated_cost_usd", 0) for r in records)
    cached = sum(1 for r in records if r.get("cached"))

    # Breakdown by model
    by_model: dict[str, dict] = {}
    for r in records:
        model = r.get("model", "unknown")
        if model not in by_model:
            by_model[model] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
        by_model[model]["requests"] += 1
        by_model[model]["tokens"] += r.get("total_tokens", 0)
        by_model[model]["cost_usd"] += r.get("estimated_cost_usd", 0)

    # Breakdown by preset
    by_preset: dict[str, dict] = {}
    for r in records:
        preset = r.get("preset_id", "unknown")
        if preset not in by_preset:
            by_preset[preset] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
        by_preset[preset]["requests"] += 1
        by_preset[preset]["tokens"] += r.get("total_tokens", 0)
        by_preset[preset]["cost_usd"] += r.get("estimated_cost_usd", 0)

    return {
        "total_requests": len(records),
        "total_tokens": total_tokens,
        "total_estimated_cost_usd": round(total_cost, 4),
        "cached_requests": cached,
        "by_model": by_model,
        "by_preset": by_preset,
    }
