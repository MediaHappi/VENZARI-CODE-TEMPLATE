#!/usr/bin/env python3
"""
[YOUR-AI-NAME] L3a: Session Logger — Capture all agent task execution details

Records every task completion with:
- Task metadata (ID, title, status)
- Execution context (prompt/summary, response/evidence)
- Outcomes (skill used, DOD verification)

Purpose: Provide raw session data for ChromaDB ingestion (Phase 5C-2)
Storage: Line-delimited JSON appended to sessions.jsonl

Usage:
  from session_logger import SessionLogger
  logger = SessionLogger()
"""

import sys
import json
import logging
import os
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("/opt/YOUR-PROJECT/.sessions")
SESSIONS_FILE = SESSIONS_DIR / "sessions.jsonl"


class SessionLogger:
    """Log task execution details to local session file."""

    def __init__(self):
        """Initialize session logger."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def log_task_completion(
        self,
        task_id: str,
        summary: str,
        evidence: str,
        skill_used: Optional[str] = None,
        task_title: Optional[str] = None,
    ) -> None:
        """
        Log a task completion with full context.

        Args:
            task_id: Task identifier (e.g., "1659")
            summary: One-sentence completion summary
            evidence: Real command output or verification proof
            skill_used: Closing skill (e.g., "code-review")
            task_title: Full task title from task JSON
        """
        session_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "task_title": task_title or "",
            "summary": summary,
            "evidence": evidence,
            "skill_used": skill_used or "",
            "status": "completed",
        }

        try:
            # Append as line-delimited JSON (JSONL format)
            with open(SESSIONS_FILE, "a") as f:
                f.write(json.dumps(session_record, ensure_ascii=False) + "\n")
            logger.info(f"Session logged for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to log session for task {task_id}: {e}")

    def read_sessions(self, task_id: Optional[str] = None) -> list:
        """
        Read session records from file.

        Args:
            task_id: Optional filter to specific task

        Returns:
            List of session records (dict)
        """
        if not SESSIONS_FILE.exists():
            return []

        records = []
        try:
            with open(SESSIONS_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if task_id is None or record.get("task_id") == task_id:
                            records.append(record)
        except Exception as e:
            logger.error(f"Failed to read sessions: {e}")

        return records

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary stats about logged sessions.

        Returns:
            Dict with counts and metadata
        """
        records = self.read_sessions()
        if not records:
            return {"total_sessions": 0, "tasks_completed": 0}

        return {
            "total_sessions": len(records),
            "tasks_completed": len(set(r.get("task_id") for r in records)),
            "first_session": records[0].get("timestamp") if records else None,
            "last_session": records[-1].get("timestamp") if records else None,
        }


if __name__ == "__main__":
    # Test usage
    logger_instance = SessionLogger()
    logger_instance.log_task_completion(
        task_id="1234",
        summary="Test task completion",
        evidence="curl http://test → HTTP 200",
        skill_used="test-driven-development",
        task_title="Test logging",
    )
    print("Session logged successfully")
    summary = logger_instance.get_session_summary()
    print(f"Session summary: {summary}")
