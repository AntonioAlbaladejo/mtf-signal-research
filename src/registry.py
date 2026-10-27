"""Append-only trial registry (PROTOCOL §2) and the hold-out access rule (PROTOCOL §3).

research/trials.jsonl is committed: every trial ever run, failed and discarded ones included,
is the input of the Deflated Sharpe Ratio and of the multiple-testing correction.
"""

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

TRIALS = Path("research/trials.jsonl")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def log(kind: str, hypothesis: str, config: dict, results: dict | None = None) -> dict:
    """Append one record, stamped with the code version it ran on."""
    record = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "hypothesis": hypothesis,
        "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12],
        "config": config,
        "code": _git("rev-parse", "--short", "HEAD"),
        # the registry itself changes with every run, so it does not make the next one dirty
        "dirty": bool(
            _git("status", "--porcelain", "--untracked-files=no", "--", ".", f":!{TRIALS}")
        ),
        "results": results or {},
    }
    TRIALS.parent.mkdir(parents=True, exist_ok=True)
    with open(TRIALS, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return record


def records() -> list[dict]:
    return [json.loads(line) for line in TRIALS.read_text().splitlines()] if TRIALS.exists() else []


def unseal(hypothesis: str, reason: str) -> None:
    """Record a hold-out access; a family (H1, H2...) gets exactly one, accidental ones included."""
    family = hypothesis.split(".")[0]
    if any(r["kind"] == "holdout" and r["hypothesis"].split(".")[0] == family for r in records()):
        raise PermissionError(f"the hold-out was already opened for family {family}")
    log("holdout", hypothesis, {"reason": reason})
