"""Immutable per-run artifact storage."""
from __future__ import annotations

import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from . import config


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run(agent_id: str, folder: str, mode: str, trial: int):
    """Create a fresh run directory; an existing one is never reused."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"{agent_id}-{mode.lower()}-t{trial:02d}-{stamp}"
    run_dir = config.RUNS_DIR / folder / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def write_once(path: Path, content) -> str:
    """Write a new artifact. Overwriting is refused."""
    if path.exists():
        raise FileExistsError(f"artifact already exists: {path}")
    if isinstance(content, str):
        config.write_text_exact(path, content)
    elif isinstance(content, bytes):
        path.write_bytes(content)
    else:
        config.dump_json(path, content)
    return config.rel(path)


def save_stage(run_dir: Path, name: str, resp) -> dict:
    """Save the raw API content of one stage, including failures."""
    paths = {}
    raw = resp.raw if resp.raw is not None else {"note": "no response body"}
    paths[f"{name}_raw_response"] = write_once(
        run_dir / f"{name}_raw_response.json", raw
    )
    if resp.text is not None:
        paths[f"{name}_raw_text"] = write_once(
            run_dir / f"{name}_raw_text.txt", resp.text
        )
    return paths


def stage_summary(name: str, resp) -> dict:
    return {
        "stage": name,
        "status": resp.status,
        "ok": resp.ok,
        "finish_reason": resp.finish_reason,
        "http_status": resp.http_status,
        "http_attempts": resp.attempts,
        "model_latency_s": round(resp.latency_s, 4),
        "model_version": resp.model_version,
        "usage": resp.usage,
        "error": resp.error,
    }


def seal(run_dir: Path) -> None:
    """Mark every artifact read-only."""
    for path in run_dir.iterdir():
        if path.is_file():
            os.chmod(path, stat.S_IREAD)
