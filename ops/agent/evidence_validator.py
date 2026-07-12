#!/usr/bin/env python3
"""
Evidence Schema Validator (Task 1828)
Classifies and validates task completion evidence against the 6 defined types.
See: docs/governance/EVIDENCE_SCHEMA.md
"""

import re
import sys
from pathlib import Path
from enum import Enum
from typing import Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False


class EvidenceType(str, Enum):
    CURL_HTTP = "CURL_HTTP"
    GIT_HASH = "GIT_HASH"
    DOCKER_STATE = "DOCKER_STATE"
    FILE_CONTENT = "FILE_CONTENT"
    TEST_PASS = "TEST_PASS"
    COMMAND_EXIT = "COMMAND_EXIT"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


# Ordered patterns — first match wins
_PATTERNS = [
    (EvidenceType.CURL_HTTP, [
        r"curl\s+http",
        r"HTTP\s+[12345]\d\d",
        r"→\s*(HTTP\s+)?[12][0-9][0-9]",
        r"http_code[\"'\s]*[12][0-9][0-9]",
        r"-w\s+['\"]%\{http_code\}",
        r"status[_\s]?code[:\s]+[12][0-9][0-9]",
        r"\bGET\b.*(200|201|204|301|302)",
        r"\bPOST\b.*(200|201|204)",
    ]),
    (EvidenceType.GIT_HASH, [
        r"git\s+(log|show|diff|commit|merge|push)",
        r"\b[0-9a-f]{7,40}\b",        # short or full SHA
        r"commit\s+[0-9a-f]{7}",
        r"git diff HEAD",
        r"HEAD~[0-9]+",
        r"→\s*[0-9a-f]{7,40}",
        r"git log.*--oneline",
    ]),
    (EvidenceType.DOCKER_STATE, [
        r"docker\s+(ps|inspect|logs|stats|exec)",
        r"\bUp\s+\d+\s+(second|minute|hour|day)",
        r"docker.*\brunning\b",
        r"container.*\bhealthy\b",
        r"docker compose",
        r"docker-compose",
    ]),
    (EvidenceType.FILE_CONTENT, [
        r"cat\s+[/\w.\-]+\s*\|?\s*grep",
        r"grep\s+['\"].*['\"]\s+[/\w.\-]+",
        r"cat\s+[/\w.\-]+\.md",
        r"diff\s+[/\w.\-]+",
        r"\|\s*grep\s+['\"]",
        r"file\s+content",
        r"→\s*\w+:.*=",         # key=value config patterns
    ]),
    (EvidenceType.TEST_PASS, [
        r"\bRan\s+\d+\s+test",
        r"\bpassed\b.*\btest",
        r"\d+\s+passed",
        r"OK\s*$",
        r"PASS(ED)?[\s\n]",
        r"pytest.*passed",
        r"npm\s+test",
        r"unittest.*OK",
        r"test.*✓",
        r"✓.*test",
        r"exit[\s_]?code[:\s]+0",
    ]),
    (EvidenceType.COMMAND_EXIT, [
        r"\$\s+\w+",             # Shell prompt with command
        r"exit[\s_]?code[:\s]+[0-9]",
        r"→\s*exit\s+[0-9]",
        r"returns?\s+[0-9]+",
        r"output:.*\w+",
        r"command.*OK",
        r"echo\s+OK",
        r"bash\s+[/\w.\-]+",
        r"python3?\s+[/\w.\-]+",
    ]),
]

# Patterns that indicate narrative / non-evidence strings
_REJECTION_PHRASES = [
    r"^it\s+(should|will|would|must|can)\s+work",
    r"^already\s+(implemented|working|done|verified)",
    r"^verified\s+existing",
    r"^scaffold\s+built",
    r"^this\s+should",
    r"^should\s+work",
    r"^confirmed\s+working",
    r"^looks\s+(good|correct|fine)",
    r"^the\s+(feature|endpoint|service)\s+(works|is\s+working)",
]


def classify(evidence: str) -> EvidenceType:
    """
    Classify evidence string into one of the 6 types.
    Returns EvidenceType.UNKNOWN if no pattern matches.
    Does NOT apply rejection rules — call validate() for full enforcement.
    """
    if not evidence or not evidence.strip():
        return EvidenceType.UNKNOWN

    text = evidence.strip()

    for ev_type, patterns in _PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return ev_type

    return EvidenceType.UNKNOWN


def validate(evidence: str) -> Tuple[bool, EvidenceType, str]:
    """
    Validate evidence for task completion.

    Returns:
        (is_valid: bool, evidence_type: EvidenceType, reason: str)

    Rejection cases:
    - Less than 20 characters
    - Matches rejection phrases (narrative assertions)
    - Evidence type is UNKNOWN (no recognizable command markers)
    """
    if not evidence or not evidence.strip():
        return False, EvidenceType.REJECTED, "Evidence is empty"

    text = evidence.strip()

    # Rule 1: Minimum length
    if len(text) < 20:
        return False, EvidenceType.REJECTED, f"Evidence too short ({len(text)} chars, minimum 20)"

    # Rule 2: Reject narrative assertions
    for pattern in _REJECTION_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            return False, EvidenceType.REJECTED, (
                f"Evidence looks like an assertion, not command output. "
                f"Matched rejection pattern: '{pattern}'. "
                f"Provide actual command output (curl, git, docker, test result)."
            )

    # Rule 3: Must match a known evidence type
    ev_type = classify(text)
    if ev_type == EvidenceType.UNKNOWN:
        return False, EvidenceType.REJECTED, (
            "Evidence has no recognizable command markers. "
            "Required: curl output, git hash/log, docker ps, test results, or command with exit code. "
            "Bad: 'Verified that endpoint works'. "
            "Good: 'curl http://localhost:5002/health → HTTP 200'"
        )

    return True, ev_type, f"Valid {ev_type.value} evidence"


def validate_or_exit(evidence: str, task_id: str = "unknown") -> EvidenceType:
    """
    Validate evidence and exit(1) if invalid. For use in task_manager.py.
    Returns the detected EvidenceType on success.
    """
    is_valid, ev_type, reason = validate(evidence)
    if not is_valid:
        print(f"\n⛔  EVIDENCE VALIDATION FAILED (Task {task_id})", file=sys.stderr)
        print(f"   {reason}", file=sys.stderr)
        print(f"   See: docs/governance/EVIDENCE_SCHEMA.md", file=sys.stderr)
        sys.exit(1)
    return ev_type


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 evidence_validator.py '<evidence string>'")
        sys.exit(1)

    evidence_text = " ".join(sys.argv[1:])
    is_valid, ev_type, reason = validate(evidence_text)

    if is_valid:
        print(f"✓ VALID [{ev_type.value}]: {reason}")
        sys.exit(0)
    else:
        print(f"✗ REJECTED: {reason}", file=sys.stderr)
        sys.exit(1)
