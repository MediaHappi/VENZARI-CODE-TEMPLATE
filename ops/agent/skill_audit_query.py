#!/usr/bin/env python3
"""
Skill Audit Query Tool (Task 1834)
Query and analyze .skill_audit.jsonl for usage tracking and performance.

Usage:
  python3 skill_audit_query.py                          — summary table of all skills
  python3 skill_audit_query.py --skill <name>           — all uses of a specific skill
  python3 skill_audit_query.py --task <task-id>         — all skills used in a task
  python3 skill_audit_query.py --failed                 — only failed loads
  python3 skill_audit_query.py --since 2026-06-01       — since ISO date prefix
  python3 skill_audit_query.py --last N                 — last N entries
  python3 skill_audit_query.py --json                   — output raw JSON lines
"""

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

import json
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent


def _load():
    from ops.agent.skill_audit import load_audit, filter_entries, skill_performance_summary
    return load_audit, filter_entries, skill_performance_summary


def _fmt(entry: dict) -> str:
    status = "✓" if entry.get("success") else "✗"
    err = f" [{entry['error']}]" if entry.get("error") else ""
    return (f"{entry.get('ts','')[:19]}  {status}  {entry.get('skill_name',''):<36}"
            f"  {entry.get('duration_ms', 0):>7.1f}ms  {entry.get('task_id',''):<8}{err}")


def main():
    args = sys.argv[1:]
    load_audit, filter_entries, skill_performance_summary = _load()

    entries = load_audit()
    if not entries:
        print("No entries in .skill_audit.jsonl")
        sys.exit(0)

    skill_filter = None
    task_filter = None
    agent_filter = None
    success_filter = None
    since_filter = None
    last_n = None
    json_out = False

    i = 0
    while i < len(args):
        if args[i] == "--skill" and i + 1 < len(args):
            skill_filter = args[i + 1]; i += 2
        elif args[i] == "--task" and i + 1 < len(args):
            task_filter = args[i + 1]; i += 2
        elif args[i] == "--agent" and i + 1 < len(args):
            agent_filter = args[i + 1]; i += 2
        elif args[i] == "--failed":
            success_filter = False; i += 1
        elif args[i] == "--success":
            success_filter = True; i += 1
        elif args[i] == "--since" and i + 1 < len(args):
            since_filter = args[i + 1]; i += 2
        elif args[i] == "--last" and i + 1 < len(args):
            last_n = int(args[i + 1]); i += 2
        elif args[i] == "--json":
            json_out = True; i += 1
        else:
            i += 1

    filtered = filter_entries(entries, skill_name=skill_filter, task_id=task_filter,
                              agent_id=agent_filter, success=success_filter,
                              since=since_filter)
    if last_n:
        filtered = filtered[-last_n:]

    if json_out:
        for e in filtered:
            print(json.dumps(e))
        return

    if skill_filter:
        # Show per-entry detail + summary
        for e in filtered:
            print(_fmt(e))
        print()
        summary = skill_performance_summary(entries, skill_filter)
        print(f"Summary for '{skill_filter}': total={summary['total']} "
              f"ok={summary['success']} fail={summary['failure']} "
              f"avg={summary.get('avg_duration_ms', 0):.1f}ms "
              f"p95={summary.get('p95_duration_ms', 0):.1f}ms")
    elif task_filter or agent_filter or success_filter is not None or since_filter or last_n:
        print(f"{'TIMESTAMP':<20} {'S':>2} {'SKILL':<36} {'MS':>8}  TASK")
        print("-" * 80)
        for e in filtered:
            print(_fmt(e))
        print(f"\n{len(filtered)} entries")
    else:
        # Default: summary table grouped by skill
        skills = sorted({e["skill_name"] for e in entries})
        print(f"{'SKILL':<40} {'TOTAL':>6} {'OK':>5} {'FAIL':>5} {'AVG(ms)':>9} {'P95(ms)':>9}")
        print("-" * 80)
        for s in skills:
            m = skill_performance_summary(entries, s)
            print(f"{s:<40} {m['total']:>6} {m['success']:>5} {m['failure']:>5} "
                  f"{m.get('avg_duration_ms', 0):>9.1f} {m.get('p95_duration_ms', 0):>9.1f}")
        print(f"\nTotal entries: {len(entries)} across {len(skills)} distinct skills")


if __name__ == "__main__":
    main()
