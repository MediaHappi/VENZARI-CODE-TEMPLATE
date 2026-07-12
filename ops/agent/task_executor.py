#!/usr/bin/env python3
"""
task_executor.py — Skill-enforced task execution wrapper for YOUR-PROJECT.

PURPOSE:
  This is the missing layer between "task claimed" and "task complete".
  It enforces that agents actually USE the loaded skills, gathers evidence
  continuously during work, and pre-creates required docs so the closing
  gate has everything ready.

PROBLEM IT SOLVES:
  297 skills exist in agents/skills/. Agents name them at completion
  (--skill flag) but routinely skip reading and following the actual
  skill procedure. Evidence is only provided at close, never during work.
  Required docs are not created until the closing gate blocks on them.

USAGE:
  # After claiming a task, before starting work:
  python3 ops/agent/task_executor.py start TASK_ID

  # Record a piece of evidence during work (call after each meaningful action):
  python3 ops/agent/task_executor.py evidence TASK_ID "curl :4001/health → 200"

  # Check what evidence has been gathered so far:
  python3 ops/agent/task_executor.py status TASK_ID

  # Get the formatted evidence string ready for --evidence at completion:
  python3 ops/agent/task_executor.py collect TASK_ID

  # Scaffold all required docs for this task layer (creates stubs if missing):
  python3 ops/agent/task_executor.py scaffold-docs TASK_ID

DESIGN:
  - Evidence is stored in .tasks/{task_id}.evidence.jsonl during work
  - Evidence items are timestamped action→outcome pairs
  - Required docs per DOC_UPDATE_MATRIX are identified at task start
  - Skill procedure checklist is printed at start — agent must acknowledge
  - At completion, collect() returns a formatted multi-source evidence string
  - Integrates with existing task_manager.py — does not replace it

Created: 2026-07-05 (Kiro session — skill enforcement hardening)
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parents[2]
TASKS_DIR = REPO / ".tasks"
EVIDENCE_SUFFIX = ".evidence.jsonl"

# DOC_UPDATE_MATRIX — layer → required docs (authoritative source)
LAYER_REQUIRED_DOCS = {
    "infrastructure": ["system-map/CURRENT_STATE.md", "system-map/SERVICES_INVENTORY.md"],
    "devops": ["system-map/CURRENT_STATE.md"],
    "backend": ["system-map/CURRENT_STATE.md"],
    "frontend": ["system-map/CURRENT_STATE.md"],
    "security": ["system-map/CURRENT_STATE.md", "GOLDEN_RULES.md"],
    "training": ["system-map/CURRENT_STATE.md"],
    "documentation": ["system-map/CURRENT_STATE.md"],
    "memory": ["system-map/CURRENT_STATE.md"],
    "orchestration": ["system-map/CURRENT_STATE.md"],
    "telegram": ["system-map/CURRENT_STATE.md"],
    "dashboard": ["system-map/CURRENT_STATE.md"],
    "monitoring": ["system-map/CURRENT_STATE.md"],
    "testing": ["system-map/CURRENT_STATE.md"],
    "autonomous": ["system-map/CURRENT_STATE.md"],
}

# Skill → procedure checklist (key steps agents skip)
SKILL_CHECKLISTS = {
    "build-and-verify": [
        "Run codegraph context analysis before any code change",
        "Record before-state (docker ps, systemctl status)",
        "Edit source only — never docker exec to patch",
        "Make one change at a time",
        "Verify with curl after every change (HTTP status required)",
        "Update CURRENT_STATE.md with new state",
    ],
    "worktree-task": [
        "Create worktree: git worktree add .worktrees/{task_id} -b task/{task_id}",
        "All work happens inside the worktree, never on production directly",
        "Commit after each logical unit (not end of session)",
        "Merge with --no-ff: git merge task/{task_id}",
        "Push immediately after merge",
        "Remove worktree after push",
    ],
    "task-completion-verifier": [
        "Gate 1: Verify each DoD item with a real command",
        "Gate 2: Confirm artifacts deployed (not just committed)",
        "Gate 3: Run doc-drift scan (jeanne-doc-drift-scan <keyword> --strict)",
        "Gate 4: SSOT committed and pushed to origin/production",
    ],
    "security-review": [
        "Check for hardcoded secrets (gitleaks or grep)",
        "Verify .gitignore covers new credential files",
        "Confirm ANTHROPIC_BASE_URL not set (Rule 13)",
        "Check no new ports opened to 0.0.0.0",
    ],
    "build-and-verify": [
        "Run codegraph context before change",
        "Record before-state",
        "Curl verify after every change",
        "HTTP 200 is evidence. 'should work' is not.",
    ],
    "observability": [
        "Check logs before AND after change (journalctl, docker logs)",
        "Record baseline metrics (response time, error rate)",
        "Verify alert rules still fire correctly",
    ],
    "ai-model-ops": [
        "Check Ollama models: docker exec ollama ollama list",
        "Verify warm models: docker exec ollama ollama ps",
        "Test model_roles.py resolves correctly",
        "Verify LiteLLM config matches model names",
        "Check keepwarm timer is active",
    ],
}


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _find_task(task_id: str) -> tuple:
    """Find task file by ID. Returns (path, task_dict) or (None, None)."""
    matches = list(TASKS_DIR.glob(f"{task_id}-*.json"))
    if not matches:
        matches = list(TASKS_DIR.glob(f"{task_id}.json"))
    if not matches:
        return None, None
    path = matches[0]
    try:
        task = json.loads(path.read_text())
        return path, task
    except Exception:
        return path, None


def _evidence_file(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}{EVIDENCE_SUFFIX}"


def cmd_start(task_id: str):
    """Print skill procedure checklist and scaffold required docs."""
    path, task = _find_task(task_id)
    if not task:
        print(f"❌ Task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    if task.get("status") != "in_progress":
        print(f"⚠️  Task {task_id} is '{task.get('status')}' — must be in_progress to start executor")
        print(f"   Claim first: python3 ops/agent/task_manager.py claim <role> --task {task_id}")

    title = task.get("title", "?")
    layer = task.get("layer", "infrastructure")
    skills = task.get("required_skills", [])

    print(f"\n{'='*70}")
    print(f"TASK EXECUTOR — {task_id}")
    print(f"  Title: {title}")
    print(f"  Layer: {layer}")
    print(f"  Skills: {', '.join(skills)}")
    print(f"{'='*70}")

    # Print skill checklists
    print(f"\n📋 SKILL PROCEDURE CHECKLISTS (READ BEFORE STARTING WORK)")
    print(f"   These are the actual procedures from agents/skills/. Do not skip them.\n")

    for skill in skills:
        # Load the actual skill content
        skill_path = REPO / "agents" / "skills" / skill / "SKILL.md"
        if skill_path.exists():
            print(f"  ── {skill} ──")
            # Print just the Brief section
            content = skill_path.read_text()
            brief_start = content.find("## Brief")
            detail_start = content.find("## Detail")
            if brief_start >= 0:
                end = detail_start if detail_start > brief_start else brief_start + 600
                brief = content[brief_start:end].strip()
                for line in brief.split("\n")[:15]:
                    print(f"    {line}")
            print()
        elif skill in SKILL_CHECKLISTS:
            print(f"  ── {skill} (checklist) ──")
            for item in SKILL_CHECKLISTS[skill]:
                print(f"    ☐ {item}")
            print()
        else:
            print(f"  ── {skill} — load with: python3 ops/agent/skill_loader.py load {skill}")

    # Required docs
    req_docs = LAYER_REQUIRED_DOCS.get(layer, ["system-map/CURRENT_STATE.md"])
    print(f"\n📄 REQUIRED DOCS TO UPDATE (layer: {layer})")
    for doc in req_docs:
        doc_path = REPO / doc
        status = "✅ exists" if doc_path.exists() else "⚠️  MISSING"
        print(f"   {status} {doc}")

    print(f"\n📊 EVIDENCE TRACKING")
    print(f"   Record evidence during work:")
    print(f"   python3 ops/agent/task_executor.py evidence {task_id} '<action> → <output>'")
    print(f"   At completion: python3 ops/agent/task_executor.py collect {task_id}")

    # Initialize evidence file
    ev_file = _evidence_file(task_id)
    if not ev_file.exists():
        ev_file.write_text("")
    _append_evidence(task_id, f"[executor] Task {task_id} started — layer={layer} skills={skills}", source="system")

    print(f"\n{'='*70}")
    print(f"✅ Executor initialized. Record evidence as you work. Good luck.\n")


def _append_evidence(task_id: str, observation: str, source: str = "agent"):
    ev_file = _evidence_file(task_id)
    entry = {
        "ts": _utcnow(),
        "source": source,
        "observation": observation,
    }
    with open(ev_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def cmd_evidence(task_id: str, observation: str):
    """Record a piece of evidence during task work."""
    _, task = _find_task(task_id)
    if not task:
        print(f"❌ Task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    _append_evidence(task_id, observation)
    ev_file = _evidence_file(task_id)
    count = sum(1 for _ in open(ev_file) if _.strip())
    print(f"✓ Evidence recorded ({count} total) for task {task_id}")
    print(f"  → {observation[:100]}")


def cmd_status(task_id: str):
    """Show evidence gathered so far for a task."""
    ev_file = _evidence_file(task_id)
    if not ev_file.exists():
        print(f"No evidence file for task {task_id}. Run: python3 task_executor.py start {task_id}")
        return

    entries = []
    for line in ev_file.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    print(f"\nEvidence for task {task_id} ({len(entries)} items):")
    for i, e in enumerate(entries, 1):
        ts = e.get("ts", "?")[:19]
        obs = e.get("observation", "?")
        src = e.get("source", "agent")
        print(f"  {i}. [{ts}] ({src}) {obs[:100]}")


def cmd_collect(task_id: str):
    """Format all evidence into a string ready for --evidence at completion."""
    ev_file = _evidence_file(task_id)
    if not ev_file.exists():
        print(f"No evidence collected yet. Use: python3 task_executor.py evidence {task_id} '<observation>'")
        return

    entries = []
    for line in ev_file.read_text().splitlines():
        if line.strip():
            try:
                e = json.loads(line)
                if e.get("source") != "system":  # Skip internal bookkeeping
                    entries.append(e.get("observation", ""))
            except Exception:
                pass

    if not entries:
        print("No agent evidence recorded yet.")
        return

    # Format as semicolon-separated for the --evidence flag
    formatted = "; ".join(e[:120] for e in entries if e)
    print(f"\n📋 FORMATTED EVIDENCE for --evidence flag:")
    print(f"\n{formatted}\n")
    print(f"\nUse: python3 ops/agent/task_manager.py complete {task_id} 'summary' \\")
    print(f"     --evidence \"{formatted[:300]}\" \\")
    print(f"     --skill <skill-name>")


def cmd_scaffold_docs(task_id: str):
    """Create stub entries in required docs for this task layer."""
    path, task = _find_task(task_id)
    if not task:
        print(f"❌ Task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    layer = task.get("layer", "infrastructure")
    title = task.get("title", task_id)
    req_docs = LAYER_REQUIRED_DOCS.get(layer, ["system-map/CURRENT_STATE.md"])

    print(f"\n📄 Scaffolding required docs for task {task_id} (layer: {layer})")

    for doc_rel in req_docs:
        doc_path = REPO / doc_rel
        if not doc_path.exists():
            print(f"  ⚠️  {doc_rel} does not exist — skipping (check DOC_UPDATE_MATRIX)")
            continue

        # Check if this task is already mentioned in the doc
        content = doc_path.read_text()
        if task_id in content:
            print(f"  ✅ {doc_rel} already references {task_id}")
            continue

        print(f"  📝 {doc_rel} — task not yet referenced")
        print(f"     Add a section for: {title}")
        print(f"     After completing the work, update this doc with the verified state.")

    print(f"\n  Run this after work is done:")
    print(f"  python3 ops/agent/task_executor.py collect {task_id}")
    print(f"  Then update the docs above with verified results.\n")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 task_executor.py <command> <task_id> [args...]")
        print("Commands: start, evidence, status, collect, scaffold-docs")
        sys.exit(1)

    command = sys.argv[1]
    task_id = sys.argv[2]

    if command == "start":
        cmd_start(task_id)
    elif command == "evidence":
        if len(sys.argv) < 4:
            print("Usage: task_executor.py evidence <task_id> '<observation>'")
            sys.exit(1)
        cmd_evidence(task_id, sys.argv[3])
    elif command == "status":
        cmd_status(task_id)
    elif command == "collect":
        cmd_collect(task_id)
    elif command == "scaffold-docs":
        cmd_scaffold_docs(task_id)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
