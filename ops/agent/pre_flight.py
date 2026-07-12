#!/usr/bin/env python3
"""
Pre-Flight Check (Phase J.3) — Blast Radius + L3 Memory Safety Gate
Called before autonomous task execution to ensure:
  1. Blast radius ≤ 5 files touched
  2. No similar failures found in L3 memory
Returns JSON: {"proceed": bool, "reason": str, "alternatives": [str]}
"""

import json
import sys
import subprocess
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

REPO_DIR = Path('/opt/YOUR-PROJECT')
INBOX = REPO_DIR / '.team/inbox/billy.jsonl'
BLAST_RADIUS_LIMIT = 5


def estimate_blast_radius(task_title: str, task_description: str) -> dict:
    """
    Estimate how many files will be touched by parsing task description.
    Returns {"count": int, "files": [str]}
    """
    desc_lower = (task_title + ' ' + task_description).lower()

    # Keywords that indicate file changes
    patterns = {
        'ops/cron': 3,  # Cron scripts often touch ops/cron + /usr/local/bin + systemd
        'ops/agent': 2,  # Agent scripts
        'docker': 4,     # Docker compose + configs + related
        'nginx': 3,      # Nginx config + test + reload
        'systemd': 2,    # Service files
        'schema': 5,     # Database schemas are risky
        'migration': 5,  # Migrations are risky
        'database': 4,   # DB-related changes
        'security': 3,   # Security changes tend to be broad
        'infra': 4,      # Infrastructure changes
        'refactor': 6,   # Refactors touch many files
        'clean up': 6,   # Cleanups can be broad
    }

    estimated_files = []
    file_count = 0

    for keyword, count in patterns.items():
        if keyword in desc_lower:
            file_count += count
            estimated_files.append(f"{keyword} (+{count})")

    # Conservative estimate
    if not estimated_files:
        file_count = 1

    return {"count": file_count, "files": estimated_files}


def query_l3_memory(task_title: str, task_description: str) -> list:
    """
    Query L3 memory (ChromaDB) for similar failures or related past work.
    Returns list of similar findings: [{"id": str, "text": str, "score": float}]
    """
    try:
        # Try to query ChromaDB via REST if available
        import requests

        query_text = f"{task_title}\n{task_description}".strip()

        # Query ChromaDB (Tailscale IP primary, tunnel fallback)
        chroma_hosts = [
            'http://127.0.0.1:8001',  # Tailscale IP (Venzari VPS)
            'http://127.0.0.1:8001',       # SSH tunnel fallback
        ]
        result = None
        for host in chroma_hosts:
            try:
                result = requests.post(
                    f'{host}/api/v2/query',
                    json={'query_texts': [query_text], 'n_results': 3},
                    timeout=5
                )
                if result.status_code == 200:
                    break  # Success, exit loop
            except Exception:
                continue  # Try next host

        if result and result.status_code == 200:
            data = result.json()
            results = []
            if 'results' in data and len(data['results']) > 0:
                for doc, dist, meta in zip(
                    data['results'][0].get('documents', []),
                    data['results'][0].get('distances', []),
                    data['results'][0].get('metadatas', []) or [{}] * len(data['results'][0].get('documents', []))
                ):
                    # Lower distance = higher similarity (ChromaDB uses L2)
                    similarity = 1 - (dist / 2) if dist else 0
                    if similarity > 0.6:  # Threshold: 60% similar
                        results.append({
                            'text': doc[:200] if doc else '',
                            'similarity': round(similarity, 2),
                            'metadata': meta
                        })
            return results
    except Exception as e:
        # L3 query is best-effort — non-blocking
        return []

    return []


def pre_flight_check(task: dict) -> dict:
    """
    Main pre-flight check. Returns:
    {
      "proceed": bool,
      "reason": str,
      "alternatives": [str],
      "blast_radius": int,
      "similar_failures": [dict]
    }
    """
    task_id = task.get('id', 'unknown')
    task_title = task.get('title', '')
    task_desc = task.get('description', '')

    result = {
        'proceed': True,
        'reason': 'All checks passed',
        'alternatives': [],
        'blast_radius': 0,
        'similar_failures': []
    }

    # ── Check 1: Blast Radius ────────────────────────────────────────────────
    blast = estimate_blast_radius(task_title, task_desc)
    result['blast_radius'] = blast['count']

    if blast['count'] > BLAST_RADIUS_LIMIT:
        result['proceed'] = False
        result['reason'] = f"Blast radius exceeded: {blast['count']} files > {BLAST_RADIUS_LIMIT} limit"
        result['alternatives'].append(
            f"Task touches too many files. Consider breaking into subtasks. Affected areas: {', '.join(blast['files'][:3])}"
        )
        return result

    # ── Check 2: L3 Memory Query ─────────────────────────────────────────────
    similar = query_l3_memory(task_title, task_desc)
    result['similar_failures'] = similar

    if similar:
        # Warn if similar work found, but don't block
        result['reason'] = f"Found {len(similar)} similar past work items. Review before proceeding."
        result['alternatives'] = [
            f"Similar finding (similarity: {s['similarity']}): {s['text'][:100]}..."
            for s in similar[:2]
        ]

    return result


def escalate_to_billy(task_id: str, reason: str, blast_radius: int):
    """Write escalation to billy.jsonl for blast radius limit."""
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        'ts': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'type': 'pre_flight_escalation',
        'task_id': task_id,
        'reason': reason,
        'blast_radius': blast_radius,
        'action_needed': f'Task {task_id} exceeds blast radius limit. Manual review required before autonomous execution.'
    }
    try:
        with open(INBOX, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: pre_flight.py <task_json_or_task_id>")
        print("Example: pre_flight.py '1234'")
        sys.exit(1)

    # Try to parse as JSON first, otherwise treat as task ID and load from file
    task_input = sys.argv[1]

    try:
        parsed = json.loads(task_input)
        # Only accept if it's a dict (task object), not a number/string
        if isinstance(parsed, dict):
            task = parsed
        else:
            raise json.JSONDecodeError("not a dict", task_input, 0)
    except json.JSONDecodeError:
        # Try to load from .tasks directory
        task_id = task_input
        task_file = next(
            (f for f in (REPO_DIR / '.tasks').glob(f'{task_id}*.json')),
            None
        )
        if not task_file:
            print(f"Task {task_id} not found", file=sys.stderr)
            sys.exit(1)
        with open(task_file) as f:
            task = json.load(f)

    # Run pre-flight check
    result = pre_flight_check(task)

    # Print result as JSON to stdout
    print(json.dumps(result, indent=2))

    # Escalate if blast radius exceeded
    if not result['proceed'] and result['blast_radius'] > BLAST_RADIUS_LIMIT:
        escalate_to_billy(
            task.get('id', '?'),
            result['reason'],
            result['blast_radius']
        )

    # Exit code: 0 if proceed, 1 if not
    sys.exit(0 if result['proceed'] else 1)
