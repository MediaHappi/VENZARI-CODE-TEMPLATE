#!/usr/bin/env python3
"""
Skill Audit Trail (Task 1834)
Logs every skill load to .skill_audit.jsonl for performance tracking and evolution.

Schema per entry:
  {ts, agent_id, skill_name, task_id, version, duration_ms, success, error}

Appends atomically via fcntl file locking (same pattern as execution_tracer.py).
Never raises — audit failures must not break skill loading.
"""

import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

REPO_DIR = Path(os.environ.get("PROJECT_CTO_PATH", "/opt/YOUR-PROJECT"))
AUDIT_FILE = REPO_DIR / ".skill_audit.jsonl"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_skill_load(
    skill_name: str,
    duration_ms: float,
    success: bool,
    agent_id: str = "agent",
    task_id: str = "",
    version: str = "",
    error: str = "",
    audit_file: Path = None,
) -> dict:
    """
    Append one audit entry to .skill_audit.jsonl.
    Returns the entry dict. Never raises.
    """
    if audit_file is None:
        audit_file = AUDIT_FILE

    entry = {
        "ts": _utcnow(),
        "agent_id": agent_id or "agent",
        "skill_name": skill_name,
        "task_id": task_id or "",
        "version": version or "",
        "duration_ms": round(float(duration_ms), 1),
        "success": bool(success),
        "error": error or "",
    }

    try:
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_file, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(entry) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass  # audit must never break skill loading

    return entry


def load_audit(path: Path = None) -> list:
    """Load all audit entries from .skill_audit.jsonl."""
    if path is None:
        path = AUDIT_FILE
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def filter_entries(
    entries: list,
    skill_name: str = None,
    task_id: str = None,
    agent_id: str = None,
    success: bool = None,
    since: str = None,
    until: str = None,
) -> list:
    """Filter audit entries by any combination of fields."""
    result = []
    for e in entries:
        if skill_name and e.get("skill_name") != skill_name:
            continue
        if task_id and e.get("task_id") != task_id:
            continue
        if agent_id and e.get("agent_id") != agent_id:
            continue
        if success is not None and e.get("success") != success:
            continue
        if since and e.get("ts", "") < since:
            continue
        if until and e.get("ts", "") > until:
            continue
        result.append(e)
    return result


def skill_performance_summary(entries: list, skill_name: str) -> dict:
    """Return {total, success, failure, avg_duration_ms, p95_duration_ms} for a skill."""
    rows = [e for e in entries if e.get("skill_name") == skill_name]
    if not rows:
        return {"skill_name": skill_name, "total": 0}
    durations = sorted(e.get("duration_ms", 0) for e in rows)
    successes = sum(1 for e in rows if e.get("success"))
    p95_idx = max(0, int(len(durations) * 0.95) - 1)
    return {
        "skill_name": skill_name,
        "total": len(rows),
        "success": successes,
        "failure": len(rows) - successes,
        "avg_duration_ms": round(sum(durations) / len(durations), 1),
        "p95_duration_ms": durations[p95_idx],
    }


if __name__ == "__main__":
    entries = load_audit()
    if not entries:
        print("No skill audit entries found in .skill_audit.jsonl")
        sys.exit(0)
    skills = sorted({e["skill_name"] for e in entries})
    print(f"{'SKILL':<40} {'TOTAL':>6} {'OK':>5} {'FAIL':>5} {'AVG(ms)':>9} {'P95(ms)':>9}")
    print("-" * 80)
    for s in skills:
        m = skill_performance_summary(entries, s)
        print(f"{s:<40} {m['total']:>6} {m['success']:>5} {m['failure']:>5} "
              f"{m.get('avg_duration_ms', 0):>9.1f} {m.get('p95_duration_ms', 0):>9.1f}")
