"""Disk cache for LLM responses.

Caches GenerateResponse JSON on disk, keyed by SHA-256 hash of the request.
Cache directory: service/cache/ (gitignored).

Canonical reference: Docs/AI_Groove_Writer_Project_Plan.md section 10.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from models import GenerateRequest, GenerateResponse

CACHE_DIR = Path(__file__).parent / "cache"


def cache_key(request: GenerateRequest) -> str:
    """Compute a SHA-256 cache key from the request fields."""
    key_data = json.dumps(
        {
            "prompt": request.prompt,
            "preset_id": request.preset_id,
            "mode": request.mode,
            "clip": request.clip.model_dump(),
            "controls": request.controls.model_dump(),
            "seed": request.seed,
            "variation": request.variation,
            "drum_map": request.drum_map,
        },
        sort_keys=True,
    )
    return hashlib.sha256(key_data.encode()).hexdigest()


def cache_get(key: str, cache_dir: Path | None = None) -> GenerateResponse | None:
    """Look up a cached response. Returns None on miss."""
    directory = cache_dir or CACHE_DIR
    path = directory / f"{key}.json"

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return GenerateResponse(**data)
    except (json.JSONDecodeError, Exception):
        return None


def cache_put(
    key: str,
    response: GenerateResponse,
    cache_dir: Path | None = None,
) -> None:
    """Write a response to the cache."""
    directory = cache_dir or CACHE_DIR
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{key}.json"
    path.write_text(
        response.model_dump_json(indent=2),
        encoding="utf-8",
    )
