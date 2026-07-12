#!/usr/bin/env python3
"""
Three Strike Rule Enforcement (Task I00007)

Rule 7: Same fix fails 3x → auto-escalate to Billy inbox
Prevents infinite loops on broken tasks.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

TASKS_DIR = Path("/opt/YOUR-PROJECT/.tasks")
INBOX = Path("/opt/YOUR-PROJECT/.team/inbox/escalations.jsonl")


def track_fix_attempt(task_id: str, error: str) -> dict:
    """
    Track a fix attempt for a task.
    Returns: {"escalated": bool, "attempt": int, "action": str}
    """
    INBOX.parent.mkdir(parents=True, exist_ok=True)

    # Load existing attempts for this task
    attempts = load_task_attempts(task_id)
    attempt_count = len(attempts) + 1

    # Log this attempt
    attempt_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "attempt": attempt_count,
        "error": error[:200],  # First 200 chars of error
    }

    # Add to log
    with open(INBOX, 'a') as f:
        f.write(json.dumps(attempt_record) + '\n')

    # Check if we've hit 3 strikes
    if attempt_count >= 3:
        escalate_task(task_id, error, attempt_count)
        return {
            "escalated": True,
            "attempt": attempt_count,
            "action": "ESCALATED to Billy inbox after 3 failures"
        }
    else:
        return {
            "escalated": False,
            "attempt": attempt_count,
            "action": f"Tracked attempt {attempt_count}/3 - will escalate on next failure"
        }


def load_task_attempts(task_id: str) -> list:
    """Load all logged attempts for a task"""
    attempts = []

    if not INBOX.exists():
        return attempts

    try:
        with open(INBOX) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get("task_id") == task_id:
                        attempts.append(record)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    return attempts


def escalate_task(task_id: str, error: str, attempt_count: int):
    """Escalate a task to Billy's inbox"""
    escalation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "three_strike_escalation",
        "task_id": task_id,
        "attempt_count": attempt_count,
        "error": error[:200],
        "action_required": f"Task {task_id} failed {attempt_count}x. Investigate root cause or mark as blocked.",
        "escalated_to": "billy",
    }

    # Create escalation task
    task_file = TASKS_DIR / f"escalation-{task_id}-strike3.json"
    escalation_task = {
        "id": f"ESC-{task_id}",
        "title": f"ESCALATED: Task {task_id} failed 3x — needs investigation",
        "status": "pending",
        "assigned_to": "billy",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_task": task_id,
        "attempts": attempt_count,
        "last_error": error[:200],
        "blocked_by": [],
    }

    with open(task_file, 'w') as f:
        json.dump(escalation_task, f, indent=2)

    # Log escalation
    with open(INBOX, 'a') as f:
        f.write(json.dumps(escalation) + '\n')


def check_task_health(task_id: str) -> dict:
    """Check if a task is at risk of escalation"""
    attempts = load_task_attempts(task_id)

    return {
        "task_id": task_id,
        "total_attempts": len(attempts),
        "at_risk": len(attempts) >= 2,  # 2+ attempts = getting close
        "escalated": len(attempts) >= 3,
        "recent_errors": [a.get("error", "") for a in attempts[-3:]] if attempts else [],
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        error = sys.argv[2] if len(sys.argv) > 2 else "Unknown error"

        result = track_fix_attempt(task_id, error)
        print(f"Task {task_id}: {result['action']}")
        if result["escalated"]:
            print(f"⚠️  ESCALATED: Escalation task created")
