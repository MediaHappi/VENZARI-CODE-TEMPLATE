#!/usr/bin/env python3
"""
ops/agent/task_manager.py
VENZARI CODE task manager — list, create, claim, complete tasks.

Usage:
  python3 ops/agent/task_manager.py list
  python3 ops/agent/task_manager.py list --status pending
  python3 ops/agent/task_manager.py create --id PROJ-001 --title "Do something" --priority high
  python3 ops/agent/task_manager.py show PROJ-001
  python3 ops/agent/task_manager.py claim PROJ-001
  python3 ops/agent/task_manager.py complete PROJ-001 --summary "Done" --evidence "Tests pass"
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone


TASKS_DIR = Path(__file__).parent.parent.parent / ".tasks"


def find_task_file(task_id: str) -> Path | None:
    """Find a task file by ID prefix match."""
    if not TASKS_DIR.exists():
        return None
    for f in TASKS_DIR.glob("*.json"):
        if f.stem.startswith(task_id) or f.stem == task_id:
            return f
    return None


def load_task(task_id: str) -> dict | None:
    path = find_task_file(task_id)
    if path is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_task(task: dict) -> None:
    TASKS_DIR.mkdir(exist_ok=True)
    task_id = task["id"]
    # Use existing file if present, otherwise create new
    existing = find_task_file(task_id)
    path = existing if existing else TASKS_DIR / f"{task_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2)
        f.write("\n")


def list_tasks(status_filter: str | None = None) -> None:
    if not TASKS_DIR.exists():
        print("No .tasks/ directory found. Run venzari-code install first.")
        return

    tasks = []
    for f in sorted(TASKS_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                task = json.load(fh)
                tasks.append(task)
        except (json.JSONDecodeError, OSError):
            continue

    if not tasks:
        print("No tasks found.")
        return

    if status_filter:
        tasks = [t for t in tasks if t.get("status") == status_filter]

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda t: (priority_order.get(t.get("priority", "medium"), 2), t.get("id", "")))

    print(f"{'ID':<35} {'PRIORITY':<10} {'STATUS':<12} TITLE")
    print("-" * 90)
    for task in tasks:
        print(f"{task.get('id','?'):<35} {task.get('priority','?'):<10} {task.get('status','?'):<12} {task.get('title','?')}")
    print(f"\n{len(tasks)} task(s)")


def show_task(task_id: str) -> None:
    task = load_task(task_id)
    if task is None:
        print(f"Task not found: {task_id}")
        sys.exit(1)
    print(json.dumps(task, indent=2))


def create_task(task_id: str, title: str, priority: str, description: str = "") -> None:
    existing = load_task(task_id)
    if existing:
        print(f"Task already exists: {task_id}")
        sys.exit(1)
    task = {
        "id": task_id,
        "title": title,
        "priority": priority,
        "description": description,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    save_task(task)
    print(f"Created: {task_id}")


def claim_task(task_id: str) -> None:
    task = load_task(task_id)
    if task is None:
        print(f"Task not found: {task_id}")
        sys.exit(1)
    if task.get("status") not in ("pending", None):
        print(f"Cannot claim task with status: {task.get('status')}")
        sys.exit(1)
    task["status"] = "in-progress"
    task["claimedAt"] = datetime.now(timezone.utc).isoformat()
    save_task(task)
    print(f"Claimed: {task_id}")


def complete_task(task_id: str, summary: str, evidence: str) -> None:
    task = load_task(task_id)
    if task is None:
        print(f"Task not found: {task_id}")
        sys.exit(1)
    task["status"] = "complete"
    task["completedAt"] = datetime.now(timezone.utc).isoformat()
    task["summary"] = summary
    task["evidence"] = evidence
    save_task(task)
    print(f"Completed: {task_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VENZARI CODE task manager")
    subparsers = parser.add_subparsers(dest="command")

    # list
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", help="Filter by status")

    # show
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("task_id")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("--id", required=True, dest="task_id")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--priority", default="medium", choices=["critical", "high", "medium", "low"])
    create_parser.add_argument("--description", default="")

    # claim
    claim_parser = subparsers.add_parser("claim", help="Claim a task")
    claim_parser.add_argument("task_id")

    # complete
    complete_parser = subparsers.add_parser("complete", help="Complete a task")
    complete_parser.add_argument("task_id")
    complete_parser.add_argument("--summary", required=True)
    complete_parser.add_argument("--evidence", required=True)

    args = parser.parse_args()

    if args.command == "list":
        list_tasks(args.status)
    elif args.command == "show":
        show_task(args.task_id)
    elif args.command == "create":
        create_task(args.task_id, args.title, args.priority, args.description)
    elif args.command == "claim":
        claim_task(args.task_id)
    elif args.command == "complete":
        complete_task(args.task_id, args.summary, args.evidence)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
