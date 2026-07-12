#!/usr/bin/env python3
"""
Memory Governance Validator (Task 1835)
Validates memory writes follow layer protocol before they are persisted.

Layer rules:
  L3 (episodic/semantic memory) → must go through claude-mem (API)
  L5 (procedural/long-term)     → must go through git + docs (file system)
  L2 (working memory)           → task-scoped data only; no L3+ data

Required metadata:
  - source_task_id: non-empty string
  - timestamp: ISO 8601 string
  - author: non-empty string (agent or "billy")

Violation levels:
  - CRITICAL: wrong layer destination (e.g. L3 data written to L2)
  - HIGH: missing required metadata
  - WARN: suspicious patterns (e.g. very short content)

Integration: Called from claude_mem_adapter.write_mem() before every write.
Violations logged to execution_tracer.py (non-blocking if tracer unavailable).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

REPO_DIR = Path(__file__).parent.parent.parent


# ── Layer definitions ──────────────────────────────────────────────────────────

LAYER_NAMES = {
    "L1": "sensory (ephemeral, discard after use)",
    "L2": "working (task-scoped, volatile)",
    "L3": "episodic/semantic (claude-mem API)",
    "L4": "procedural (code + skills)",
    "L5": "declarative/long-term (git + docs)",
}

# Which write destination is legal for each layer
LAYER_DESTINATIONS = {
    "L3": "claude-mem",
    "L5": "git+docs",
    "L2": "task-scope",
    "L4": "code",
    "L1": "ephemeral",
}

# Keywords that signal L3/L5 content (long-term memory markers)
L3_SIGNALS = ["observation:", "memory:", "learned:", "insight:", "[task:", "[scope:", "[branch:"]
L5_SIGNALS = ["decision:", "adr:", "rule:", "policy:", "approved:", "golden rule"]

REQUIRED_METADATA = ["source_task_id", "timestamp", "author"]

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    severity: str   # CRITICAL | HIGH | WARN
    field: str
    message: str


@dataclass
class GovernanceResult:
    valid: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "violations": [{"severity": v.severity, "field": v.field, "message": v.message}
                           for v in self.violations],
            "warnings": self.warnings,
        }


# ── Validation checks ─────────────────────────────────────────────────────────

def _check_required_metadata(metadata: dict) -> List[Violation]:
    violations = []
    for field_name in REQUIRED_METADATA:
        val = metadata.get(field_name, "")
        if not val or not str(val).strip():
            violations.append(Violation(
                severity="HIGH",
                field=field_name,
                message=f"Required metadata field '{field_name}' is missing or empty",
            ))
    # Validate timestamp format
    ts = metadata.get("timestamp", "")
    if ts and not ISO_RE.match(str(ts)):
        violations.append(Violation(
            severity="HIGH",
            field="timestamp",
            message=f"timestamp must be ISO 8601 format (got: '{ts}')",
        ))
    return violations


def _check_layer_destination(
    content: str,
    destination: str,
    declared_layer: str = "",
) -> List[Violation]:
    """
    Check that the write destination is appropriate for the content's layer.
    destination: "claude-mem" | "git+docs" | "task-scope" | "code" | "ephemeral"
    """
    violations = []
    content_lower = content.lower()

    # Detect content signals
    has_l5_signals = any(sig in content_lower for sig in L5_SIGNALS)
    has_l3_signals = any(sig in content_lower for sig in L3_SIGNALS)

    # L5 content must not be written to claude-mem (should go to git+docs)
    if destination == "claude-mem" and has_l5_signals and not has_l3_signals:
        violations.append(Violation(
            severity="CRITICAL",
            field="layer_destination",
            message=(
                "Content appears to be L5 (declarative/policy) but destination is claude-mem. "
                "L5 writes must go to git+docs (CURRENT_STATE.md, GOLDEN_RULES.md, ADR files)."
            ),
        ))

    # L3 content must not be written to git+docs directly
    if destination == "git+docs" and has_l3_signals and not has_l5_signals:
        violations.append(Violation(
            severity="CRITICAL",
            field="layer_destination",
            message=(
                "Content appears to be L3 (episodic/semantic) but destination is git+docs. "
                "L3 writes must go through claude-mem API."
            ),
        ))

    # L2 (task-scope) must not contain L3+ signals
    if destination == "task-scope" and (has_l3_signals or has_l5_signals):
        violations.append(Violation(
            severity="CRITICAL",
            field="layer_destination",
            message=(
                "L2 (working memory / task-scope) write contains L3 or L5 signals. "
                "Use claude-mem for L3 data or git+docs for L5 data."
            ),
        ))

    return violations


def _check_content_quality(content: str) -> List[str]:
    warnings = []
    if len(content.strip()) < 20:
        warnings.append("Content is very short (<20 chars) — memory write may be incomplete")
    if content.count("\n") > 200:
        warnings.append("Content is very long (>200 lines) — consider chunking")
    return warnings


# ── Public API ────────────────────────────────────────────────────────────────

def validate_write(
    content: str,
    destination: str,
    metadata: Optional[dict] = None,
    declared_layer: str = "",
) -> GovernanceResult:
    """
    Validate a memory write.

    Args:
        content: The memory content to be written
        destination: Where the write is going ("claude-mem", "git+docs", "task-scope", "code", "ephemeral")
        metadata: Dict with source_task_id, timestamp, author
        declared_layer: Optional layer hint (e.g. "L3")

    Returns:
        GovernanceResult with valid=True if no CRITICAL/HIGH violations.
    """
    if metadata is None:
        metadata = {}

    violations: List[Violation] = []
    violations += _check_required_metadata(metadata)
    violations += _check_layer_destination(content, destination, declared_layer)
    warnings = _check_content_quality(content)

    # Only CRITICAL or HIGH violations make the write invalid
    blocking = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
    valid = len(blocking) == 0

    result = GovernanceResult(valid=valid, violations=violations, warnings=warnings)

    # Log violation to execution_tracer if available
    if not valid:
        try:
            from ops.agent.execution_tracer import trace_error
            task_id = str(metadata.get("source_task_id", ""))
            msg = "; ".join(v.message for v in blocking[:3])
            trace_error(task_id=task_id, error_type="memory_governance_violation", message=msg)
        except Exception:
            pass

        # Export violations as findings for wiki ingestion
        create_governance_finding(blocking, destination)

    return result


def create_governance_finding(violations: List[Violation], destination: str):
    """REAL: Export governance violations as findings → wiki"""
    try:
        if not violations:
            return
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        for violation in violations:
            incident = Incident(
                id=f"incident-governance-{hash(violation.message) % 1000000}-{int(datetime.now().timestamp())}",
                service="memory-governance",
                incident_type=IncidentType.VALIDATION_FAILURE,
                severity=IncidentSeverity.HIGH if violation.level == "CRITICAL" else IncidentSeverity.MEDIUM,
                timestamp=datetime.now(timezone.utc).isoformat(),
                title=f"Memory governance {violation.level}: {destination}",
                evidence=[{"type": "governance", "text": violation.message}],
                related_metrics={"destination": destination, "violation_level": violation.level}
            )

            finding = finding_creator.create_finding_from_incident(incident)
            findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def validate_or_exit(content: str, destination: str, metadata: Optional[dict] = None,
                     declared_layer: str = "") -> GovernanceResult:
    """Run validate_write and exit 1 if invalid."""
    result = validate_write(content, destination, metadata, declared_layer)
    if not result.valid:
        print("\n⛔  MEMORY GOVERNANCE VIOLATION — write blocked", file=sys.stderr)
        for v in result.violations:
            print(f"   [{v.severity}] {v.field}: {v.message}", file=sys.stderr)
        sys.exit(1)
    return result


if __name__ == "__main__":
    import json
    print("Memory Governance Validator — interactive check")
    print("Usage: echo 'content' | python3 memory_governance_validator.py <destination> [source_task_id]")
    if len(sys.argv) >= 2:
        dest = sys.argv[1]
        task_id = sys.argv[2] if len(sys.argv) > 2 else "test"
        content = sys.stdin.read() if not sys.stdin.isatty() else "sample memory content"
        metadata = {
            "source_task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": "agent",
        }
        result = validate_write(content, dest, metadata)
        print(json.dumps(result.as_dict(), indent=2))
        sys.exit(0 if result.valid else 1)
