#!/usr/bin/env python3
"""
YOUR-PROJECT Worktree Manager — Isolated execution per task.
Usage:
  python3 worktree.py create TASK_ID         # create isolated worktree
  python3 worktree.py list                   # show active worktrees
  python3 worktree.py complete TASK_ID       # merge and remove worktree
  python3 worktree.py abandon TASK_ID        # remove without merging
"""
import json
import os
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

REPO = Path('/opt/YOUR-PROJECT')
WORKTREES = REPO / '.worktrees'
WORKTREES.mkdir(exist_ok=True)


def run(cmd, cwd=None, check=True):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(cwd or REPO))
    if check and result.returncode != 0:
        print(f"ERROR: {cmd}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def create_worktree(task_id):
    wt_path = WORKTREES / task_id
    branch = f"task/{task_id}"

    if wt_path.exists():
        print(f"Worktree already exists: {wt_path}")
        return str(wt_path)

    # Create branch and worktree
    run(f"git worktree add {wt_path} -b {branch} HEAD")
    print(f"Created worktree: {wt_path}")
    print(f"Branch: {branch}")
    print(f"Work in: {wt_path}")

    # Write context file for agent
    ctx = {
        'task_id': task_id,
        'branch': branch,
        'worktree_path': str(wt_path),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'instructions': f"Make changes in {wt_path}, then run: python3 {REPO}/ops/agent/worktree.py complete {task_id}"
    }
    with open(wt_path / '.task_context.json', 'w') as f:
        json.dump(ctx, f, indent=2)

    return str(wt_path)


def list_worktrees():
    result = run("git worktree list --porcelain", check=False)
    print(result)
    wt_dirs = list(WORKTREES.iterdir()) if WORKTREES.exists() else []
    active = [d for d in wt_dirs if d.is_dir()]
    print(f"\nActive worktrees in .worktrees/: {len(active)}")
    for d in sorted(active):
        ctx_file = d / '.task_context.json'
        if ctx_file.exists():
            ctx = json.loads(ctx_file.read_text())
            print(f"  {d.name}: branch={ctx.get('branch')}, created={ctx.get('created_at','?')[:10]}")
        else:
            print(f"  {d.name}")


def complete_worktree(task_id):
    wt_path = WORKTREES / task_id
    if not wt_path.exists():
        print(f"Worktree {task_id} not found")
        return

    branch = f"task/{task_id}"

    # Check for uncommitted changes (ignore untracked files)
    status = run(f"git status --short", cwd=wt_path, check=False)
    # Filter out untracked lines (those starting with ??)
    tracked_changes = [l for l in status.splitlines() if not l.startswith('??')]
    if tracked_changes:
        print(f"Uncommitted staged/modified changes in worktree:\n" + '\n'.join(tracked_changes))
        print("Commit or stash before completing.")
        return

    # Switch to main and merge
    run(f"git checkout main")
    result = subprocess.run(
        f"git merge --no-ff {branch} -m 'Merge task/{task_id}'",
        shell=True, capture_output=True, text=True, cwd=str(REPO)
    )
    if result.returncode != 0:
        print(f"Merge failed:\n{result.stderr}\nResolve manually.")
        return

    # Remove worktree
    run(f"git worktree remove {wt_path} --force")
    run(f"git branch -d {branch}", check=False)
    print(f"Worktree {task_id} merged and removed")


def abandon_worktree(task_id):
    wt_path = WORKTREES / task_id
    if wt_path.exists():
        run(f"git worktree remove {wt_path} --force")
        run(f"git branch -D task/{task_id}", check=False)
        print(f"Worktree {task_id} abandoned")
    else:
        print(f"Worktree {task_id} not found")


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'list':
        list_worktrees()
    elif a[0] == 'create' and len(a) >= 2:
        create_worktree(a[1])
    elif a[0] == 'complete' and len(a) >= 2:
        complete_worktree(a[1])
    elif a[0] == 'abandon' and len(a) >= 2:
        abandon_worktree(a[1])
    else:
        print(__doc__)
        sys.exit(1)
