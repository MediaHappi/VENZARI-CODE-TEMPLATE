#!/usr/bin/env python3
"""
Task Anti-Drift Scanner (Task 1314)
Detects tasks claiming work outside their stated scope
Runs daily as cron check and session startup
"""

import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_DIR = Path("/opt/YOUR-PROJECT")
TASKS_DIR = REPO_DIR / ".tasks"
INBOX = REPO_DIR / ".team/inbox/billy.jsonl"
DOC_MATRIX_PATH = REPO_DIR / "docs/governance/DOC_UPDATE_MATRIX.md"

# Maps task layer values to DOC_UPDATE_MATRIX.md section headers (bullet-format parsing
# path only — parse_doc_matrix()'s table-format path, which is what DOC_UPDATE_MATRIX.md
# actually uses today, doesn't consult this dict at all). Extended from 7 to the full
# 16 layer codes per task_numbering.py (H-004, 2026-07-02) so a future bullet-format
# section for any layer resolves correctly instead of silently degrading to
# CURRENT_STATE.md-only.
LAYER_TO_SECTION = {
    "infrastructure": "Infrastructure Tasks", "I": "Infrastructure Tasks",
    "backend": "Backend/Code Tasks", "B": "Backend/Code Tasks",
    "frontend": "Backend/Code Tasks", "F": "Backend/Code Tasks",
    "devops": "Infrastructure Tasks", "D": "Infrastructure Tasks",
    "data": "Backend/Code Tasks", "A": "Backend/Code Tasks",
    "training": "Backend/Code Tasks", "R": "Backend/Code Tasks",
    "orchestration": "Governance/Meta Tasks", "O": "Governance/Meta Tasks",
    "testing": "Testing Tasks", "T": "Testing Tasks",
    "security": "Security Tasks", "S": "Security Tasks",
    "memory": "Memory/Context Tasks", "M": "Memory/Context Tasks",
    "telegram": "Interface Tasks", "C": "Interface Tasks",
    "dashboard": "Interface Tasks", "H": "Interface Tasks",
    "monitoring": "Monitoring Tasks", "L": "Monitoring Tasks",
    "documentation": "Governance/Meta Tasks", "E": "Governance/Meta Tasks",
    "autonomous": "Governance/Meta Tasks", "U": "Governance/Meta Tasks",
    "uncategorized": "Governance/Meta Tasks", "X": "Governance/Meta Tasks",
    "governance": "Governance/Meta Tasks", "00-foundation": "Governance/Meta Tasks",
}


def check_code_changes(task: dict) -> dict:
    """
    Task I0000000033: Check if code changes match task scope (ops/agent/, tests/, etc.).
    For backend/infrastructure tasks, expect code changes.
    Returns: {"status": "ok|warning|missing", "code_files": [...], "message": "..."}
    """
    layer = task.get('layer', '')
    changed_files = get_changed_docs_since(task.get('claimed_at'))

    # Code file patterns by layer
    code_patterns = {
        'backend': ['ops/agent/', 'ops/backend/', 'src/'],
        'infrastructure': ['ops/agent/', 'ops/infra/', 'docker-compose.yml', '.env'],
        'testing': ['ops/tests/', 'tests/'],
        'security': ['ops/security/', 'ops/agent/'],
    }

    relevant_patterns = code_patterns.get(layer, ['ops/'])
    code_files = [f for f in changed_files if any(pat in f for pat in relevant_patterns)]

    # Only warn if layer typically involves code but no code changed
    if layer in code_patterns and not code_files:
        return {
            "status": "warning",
            "code_files": code_files,
            "message": f"Layer '{layer}' typically involves code changes; none detected"
        }

    return {"status": "ok", "code_files": code_files, "message": "Code changes detected" if code_files else "No code changes expected"}


def check_config_changes(task: dict) -> dict:
    """
    Task I0000000033: Check if infrastructure config changes (docker-compose, systemd, etc.) are in scope.
    Returns: {"status": "ok|drift", "config_files": [...], "message": "..."}
    """
    changed_files = get_changed_docs_since(task.get('claimed_at'))

    # Infrastructure config patterns
    config_patterns = [
        'docker-compose.yml', 'docker-compose.yaml',
        '*.service',  # systemd services
        'ops/automation/', 'ops/configs/',
        '.env', '.env.example',
        'Makefile', 'Dockerfile',
    ]

    config_files = []
    for f in changed_files:
        if any(pat in f for pat in config_patterns) or f.endswith(('.service', '.yml', '.yaml', '.toml', '.ini')):
            config_files.append(f)

    return {
        "status": "ok",
        "config_files": config_files,
        "message": f"Found {len(config_files)} config changes" if config_files else "No config changes"
    }


def get_changed_docs_since(claimed_at: str) -> list:
    """Return list of file paths changed in git since claimed_at (committed + staged + unstaged)."""
    changed = set()

    # Committed files since claimed_at
    if claimed_at:
        try:
            result = subprocess.run(
                ["git", "-C", str(REPO_DIR), "log", f"--since={claimed_at}",
                 "--name-only", "--format="],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    changed.add(line)
        except Exception:
            pass

    # Staged changes
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "diff", "--cached", "--name-only"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                changed.add(line)
    except Exception:
        pass

    # Unstaged changes
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_DIR), "diff", "--name-only"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                changed.add(line)
    except Exception:
        pass

    return list(changed)


def parse_doc_matrix(layer: str) -> list:
    """
    Parse DOC_UPDATE_MATRIX.md and return required doc filenames for a task layer.
    Handles both bullet-point format (- **file**) and table format (| layer | docs |).
    Always includes mandatory docs.
    """
    if not DOC_MATRIX_PATH.exists():
        return ["system-map/CURRENT_STATE.md"]

    try:
        content = DOC_MATRIX_PATH.read_text()
    except Exception:
        return ["system-map/CURRENT_STATE.md"]

    docs = []
    seen = set()

    # Parse TABLE format: | **layer** | doc1, doc2, doc3 | optional | examples |
    for line in content.splitlines():
        if "|" in line and "**" in line:
            # Check if this line contains our layer
            if f"**{layer}**" in line:
                # Split by | and get the second column (mandatory docs)
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    mandatory_docs_col = parts[2]  # Second column is mandatory docs
                    # Parse comma-separated docs
                    for doc_entry in mandatory_docs_col.split(","):
                        doc = doc_entry.strip()
                        if doc and doc not in seen:
                            # Bare .md filenames default to system-map/ (where most of
                            # them live) UNLESS the file actually exists at repo root
                            # instead — e.g. GOLDEN_RULES.md, CLAUDE.md, README.md are
                            # root-level, not under system-map/. Blindly prefixing
                            # produced a path that never existed (harmless for matching
                            # since verify_doc_updates compares by filename, not full
                            # path, but misleading — fixed 2026-07-02).
                            # CURRENT_STATE.md is a forced exception: a STALE root copy
                            # also exists (pending removal, see task E0000000009 / M-002)
                            # — system-map/CURRENT_STATE.md is the canonical one per
                            # CLAUDE.md regardless of which copy happens to exist.
                            if "/" not in doc and doc.endswith(".md"):
                                if doc == "CURRENT_STATE.md":
                                    doc = "system-map/CURRENT_STATE.md"
                                elif not (REPO_DIR / doc).exists() and (REPO_DIR / "system-map" / doc).exists():
                                    doc = f"system-map/{doc}"
                            seen.add(doc)
                            docs.append(doc)

    # Parse BULLET format: - **filename**
    current_section = None
    required_section = LAYER_TO_SECTION.get(layer, "")
    sections_to_parse = {"All Tasks (Mandatory)"}
    if required_section:
        sections_to_parse.add(required_section)

    for line in content.splitlines():
        # Detect section headers (### Section Name)
        if line.startswith("### "):
            section_name = line[4:].strip()
            current_section = section_name if any(s in section_name for s in sections_to_parse) else None
            continue

        # Extract bold doc names from bullet points
        if current_section and line.strip().startswith("- **"):
            match = re.search(r"\*\*([^*]+\.(md|json|py|sh|yaml|yml))\*\*", line)
            if match:
                doc = match.group(1)
                if doc not in seen:
                    seen.add(doc)
                    docs.append(doc)

    # Always require CURRENT_STATE.md as minimum
    if not any("CURRENT_STATE" in d for d in docs):
        docs.append("system-map/CURRENT_STATE.md")

    return docs


def refresh_repo_map_if_stale() -> None:
    """Task O0000000005: keep the codegraph-backed repo map current by piggybacking on
    drift_scanner's existing gate-point invocations, rather than adding a separate git
    hook. Non-fatal -- repo_map.py or the codegraph index being unavailable should never
    block a task completion over an unrelated feature."""
    try:
        sys.path.insert(0, str(REPO_DIR / "ops" / "agent"))
        from repo_map import ensure_fresh
        ensure_fresh()
    except Exception:
        pass


def verify_all_drift(task: dict) -> dict:
    """
    Task I0000000033: Comprehensive drift check - docs, code, and config.
    Returns: {"status": "ok|warning|missing", "docs": {...}, "code": {...}, "config": {...}}
    """
    refresh_repo_map_if_stale()

    result = {
        "status": "ok",
        "docs": verify_doc_updates(task),
        "code": check_code_changes(task),
        "config": check_config_changes(task),
    }

    # Set overall status to most severe
    statuses = [result['docs'].get('status'), result['code'].get('status'), result['config'].get('status')]
    if 'missing' in statuses:
        result['status'] = 'missing'
    elif 'warning' in statuses:
        result['status'] = 'warning'

    return result


def verify_doc_updates(task: dict) -> dict:
    """
    Advanced doc update verification - multiple detection methods.

    Checks three sources:
    1. DoD items starting with 'UPDATE:' — explicit doc requirements
    2. DOC_UPDATE_MATRIX.md — task-type-based requirements
    3. Git history + evidence + commit messages — smart detection of actual updates

    Returns:
        {"status": "ok"}
        {"status": "missing", "missing_docs": [...], "changed_docs": [...]}
        {"status": "skip", "reason": "..."}
    """
    claimed_at = task.get('claimed_at')
    task_layer = task.get('layer', '')
    evidence = task.get('evidence', '')

    # Method 1: Git history - docs changed since claim
    changed_docs = get_changed_docs_since(claimed_at)
    changed_filenames = {Path(p).name for p in changed_docs}
    changed_paths = set(changed_docs)

    # Method 2: Evidence mentions - smart detection from task evidence/summary
    evidence_text = (evidence or '') + ' ' + (task.get('summary', '') or '')
    mentioned_docs = set()
    for doc_candidate in ['/system-map/', '/docs/', '/ops/', 'CURRENT_STATE', 'MASTER_EXECUTION', 'README', 'GOLDEN_RULES']:
        if doc_candidate.lower() in evidence_text.lower():
            mentioned_docs.add(doc_candidate)

    # Method 3: Commit history - check recent commits for doc changes
    try:
        cmd = f"git -C {REPO_DIR} diff HEAD~1..HEAD --name-only 2>/dev/null || git -C {REPO_DIR} status --short 2>/dev/null"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if result.stdout:
            changed_docs.update(result.stdout.strip().split('\n'))
    except:
        pass

    # Aggregate all evidence of doc updates
    all_changed = changed_filenames | changed_paths | mentioned_docs

    # Source 1: Explicit UPDATE: items in DoD
    explicit_docs = []
    for dod_item in task.get('dod', []):
        item_text = dod_item.get('item', '')
        if item_text.upper().startswith('UPDATE:'):
            doc_path = item_text[7:].strip()
            explicit_docs.append(doc_path)

    # Source 2: DOC_UPDATE_MATRIX.md required docs for this task layer
    matrix_docs = parse_doc_matrix(task_layer)

    all_required = list({*explicit_docs, *matrix_docs})
    missing = []

    for required_doc in all_required:
        doc_filename = Path(required_doc).name
        # Smart matching: check git changes, mentioned in evidence, or filename match
        is_changed = (
            doc_filename in changed_filenames
            or any(required_doc in str(p) or doc_filename in str(p) for p in all_changed)
            or doc_filename.lower() in evidence_text.lower()
        )
        if not is_changed:
            missing.append(required_doc)

    if missing:
        return {
            "status": "missing",
            "missing_docs": missing,
            "changed_docs": sorted(list(all_changed)),
        }

    return {"status": "ok", "changed_docs": sorted(list(all_changed))}

def get_task_commits(task_id: str, since_time: str = None) -> list:
    """Get commits related to a task ID in last 24h."""
    try:
        cmd = f"git -C {REPO_DIR} log --oneline --grep={task_id} -n 20"
        if since_time:
            cmd += f" --since='{since_time}'"

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception:
        return []

def analyze_drift(task_id: str, task_json: dict) -> dict:
    """Analyze potential drift in a task."""
    claimed_at = task_json.get('claimed_at')
    if not claimed_at:
        return {"status": "ok"}

    try:
        claimed_dt = datetime.fromisoformat(claimed_at)
        now = datetime.now(timezone.utc)
        hours_claimed = (now - claimed_dt).total_seconds() / 3600

        drift_signals = []

        # Check 1: Task >24h with no commits
        if hours_claimed > 24:
            commits = get_task_commits(task_id, claimed_at)
            if not commits or (len(commits) == 1 and not commits[0]):
                drift_signals.append({
                    "type": "stale_no_commits",
                    "severity": "high",
                    "evidence": f"No commits in {int(hours_claimed)}h since claimed"
                })

        # Check 2: Task >4h with no progress
        if 4 < hours_claimed < 24:
            commits = get_task_commits(task_id, claimed_at)
            if not commits or len(commits) < 1:
                drift_signals.append({
                    "type": "stalled_progress",
                    "severity": "medium",
                    "evidence": f"No commits in {int(hours_claimed)}h"
                })

        # Check 3: Summary missing but hours have passed
        if hours_claimed > 2 and not task_json.get('summary'):
            drift_signals.append({
                "type": "no_summary",
                "severity": "low",
                "evidence": f"Claimed {int(hours_claimed)}h ago, no summary yet"
            })

        if drift_signals:
            return {
                "status": "drift_detected",
                "task_id": task_id,
                "hours_claimed": round(hours_claimed, 1),
                "signals": drift_signals
            }

        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def scan_all_tasks() -> list:
    """Scan all in_progress tasks for drift."""
    drifted_tasks = []

    try:
        for task_file in TASKS_DIR.glob("*.json"):
            with open(task_file) as f:
                task = json.load(f)

            if task.get('status') == 'in_progress':
                result = analyze_drift(task.get('id'), task)
                if result.get('status') == 'drift_detected':
                    drifted_tasks.append(result)

    except Exception as e:
        print(f"Error scanning tasks: {e}", file=sys.stderr)

    return drifted_tasks

def escalate_drift(drifted_tasks: list):
    """Write critical drift to billy.jsonl."""
    critical = [t for t in drifted_tasks if any(
        s.get('severity') == 'high' for s in t.get('signals', [])
    )]

    if critical:
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        for drift in critical:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": "task_drift_detected",
                "task_id": drift["task_id"],
                "hours_claimed": drift["hours_claimed"],
                "signals": drift["signals"],
                "action": "Review task progress; consider resetting to pending if stalled"
            }
            try:
                with open(INBOX, 'a') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception:
                pass

if __name__ == "__main__":
    drifted = scan_all_tasks()

    if drifted:
        logger.warning(f"⚠️  Task Drift Detected ({len(drifted)} tasks):")
        for drift in drifted:
            logger.warning(f"\n  Task {drift['task_id']} (claimed {drift['hours_claimed']}h ago)")
            for signal in drift['signals']:
                logger.warning(f"    - [{signal['severity'].upper()}] {signal['type']}: {signal['evidence']}")

        # Escalate critical drift
        escalate_drift(drifted)

        # Return result instead of exiting (allow callers to handle)
        has_high_severity = any(s.get('severity') == 'high' for d in drifted for s in d.get('signals', []))
        if has_high_severity:
            raise ValueError(f"Task drift detected: {len(drifted)} drifted tasks with high-severity signals")
        else:
            logger.info(f"Task drift detected but no high-severity signals: {len(drifted)} tasks")
    else:
        logger.info("✓ No task drift detected")
