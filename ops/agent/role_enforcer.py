#!/usr/bin/env python3
"""
Role Enforcer (Task 1836 — P2-4)
Enforces that a claiming agent's role matches the task's required_role at claim time.

Agent registry: .agents/registry.json
  {"agent_id": {"role": "backend", "display_name": "Backend Agent"}, ...}

Roles (VALID_ROLES from task_manager.py):
  infrastructure, backend, memory, frontend, security, testing, documentation, unassigned

Claim enforcement:
  1. Look up agent_id in registry → get current role
  2. Compare to task's agent_role field
  3. Block if mismatch; allow with --force-role (escalates to billy.jsonl)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

REPO_DIR = Path(os.environ.get("PROJECT_CTO_PATH", "/opt/YOUR-PROJECT"))
REGISTRY_PATH = REPO_DIR / ".agents" / "registry.json"
INBOX_PATH = REPO_DIR / ".team" / "inbox" / "billy.jsonl"

VALID_ROLES = {
    "infrastructure", "backend", "memory", "frontend",
    "security", "testing", "documentation", "unassigned",
}

DEFAULT_REGISTRY = {
    "infrastructure": {"role": "infrastructure", "display_name": "Infrastructure Agent"},
    "backend": {"role": "backend", "display_name": "Backend Agent"},
    "memory": {"role": "memory", "display_name": "Memory Agent"},
    "frontend": {"role": "frontend", "display_name": "Frontend Agent"},
    "security": {"role": "security", "display_name": "Security Agent"},
    "testing": {"role": "testing", "display_name": "Testing Agent"},
    "documentation": {"role": "documentation", "display_name": "Documentation Agent"},
    "agent": {"role": "unassigned", "display_name": "Generic Agent"},
}


# ── Registry management ───────────────────────────────────────────────────────

def load_registry(path: Path = None) -> dict:
    """Load agent registry from .agents/registry.json. Falls back to DEFAULT_REGISTRY."""
    if path is None:
        path = REGISTRY_PATH
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return dict(DEFAULT_REGISTRY)


def save_registry(registry: dict, path: Path = None) -> None:
    if path is None:
        path = REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(registry, f, indent=2)
    os.rename(tmp, str(path))


def register_agent(agent_id: str, role: str, display_name: str = "",
                   registry_path: Path = None) -> dict:
    """Register or update an agent in the registry."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Valid: {', '.join(sorted(VALID_ROLES))}")
    registry = load_registry(registry_path)
    registry[agent_id] = {
        "role": role,
        "display_name": display_name or f"{role.title()} Agent",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    save_registry(registry, registry_path)
    return registry[agent_id]


def get_agent_role(agent_id: str, registry_path: Path = None) -> Optional[str]:
    """Return the registered role for agent_id, or None if not found."""
    registry = load_registry(registry_path)
    entry = registry.get(agent_id)
    if entry:
        return entry.get("role")
    # Convention: if agent_id IS a valid role name, treat it as that role
    if agent_id in VALID_ROLES:
        return agent_id
    return None


# ── Enforcement ───────────────────────────────────────────────────────────────

@dataclass
class RoleCheckResult:
    allowed: bool
    agent_id: str
    agent_role: Optional[str]
    required_role: str
    reason: str
    forced: bool = False


def check_role_match(
    agent_id: str,
    task: dict,
    force_role: bool = False,
    registry_path: Path = None,
) -> RoleCheckResult:
    """
    Check if agent_id is allowed to claim a task.

    Returns RoleCheckResult.allowed=True if:
    - task has no required role ("" or "unassigned")
    - agent's role matches task's agent_role
    - force_role=True (override, escalated to inbox)
    """
    required_role = task.get("agent_role", "") or ""

    # No role requirement → anyone can claim
    if not required_role or required_role == "unassigned":
        return RoleCheckResult(
            allowed=True,
            agent_id=agent_id,
            agent_role=None,
            required_role=required_role,
            reason="No role requirement on task — open to any agent",
        )

    agent_role = get_agent_role(agent_id, registry_path)

    if agent_role is None:
        # Unknown agent: allow but warn (don't block unregistered agents)
        return RoleCheckResult(
            allowed=True,
            agent_id=agent_id,
            agent_role=None,
            required_role=required_role,
            reason=f"Agent '{agent_id}' not in registry — claiming without role validation",
        )

    if agent_role == required_role:
        return RoleCheckResult(
            allowed=True,
            agent_id=agent_id,
            agent_role=agent_role,
            required_role=required_role,
            reason=f"Role match: {agent_role} == {required_role}",
        )

    # Mismatch
    if force_role:
        _escalate_force_claim(agent_id, agent_role, required_role, task)
        return RoleCheckResult(
            allowed=True,
            agent_id=agent_id,
            agent_role=agent_role,
            required_role=required_role,
            reason=f"Role mismatch overridden with --force-role (escalated to inbox)",
            forced=True,
        )

    return RoleCheckResult(
        allowed=False,
        agent_id=agent_id,
        agent_role=agent_role,
        required_role=required_role,
        reason=(
            f"Role mismatch: agent '{agent_id}' has role '{agent_role}' "
            f"but task requires '{required_role}'"
        ),
    )


def enforce_or_exit(
    agent_id: str,
    task: dict,
    force_role: bool = False,
    registry_path: Path = None,
) -> RoleCheckResult:
    """Run check_role_match and exit 1 if blocked."""
    result = check_role_match(agent_id, task, force_role, registry_path)
    if not result.allowed:
        task_id = task.get("id", "?")
        task_title = task.get("title", "?")
        required = result.required_role
        actual = result.agent_role or "unknown"
        print(f"\n⛔  CLAIM BLOCKED — role mismatch", file=sys.stderr)
        print(f"   Task:          [{task_id}] {task_title}", file=sys.stderr)
        print(f"   This task requires role: {required}", file=sys.stderr)
        print(f"   Your agent role:         {actual}", file=sys.stderr)
        print(f"\n   To override: add --force-role flag (escalates to billy.jsonl)", file=sys.stderr)
        print(f"   To register:  python3 ops/agent/role_enforcer.py register {agent_id} {required}", file=sys.stderr)
        sys.exit(1)
    if result.forced:
        print(f"⚠ Role override: {result.reason}", file=sys.stderr)
    return result


def _escalate_force_claim(
    agent_id: str,
    agent_role: Optional[str],
    required_role: str,
    task: dict,
) -> None:
    """Write a force-claim notice to billy.jsonl."""
    try:
        INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "force_role_claim",
            "task_id": task.get("id"),
            "task_title": task.get("title"),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "required_role": required_role,
            "message": (
                f"Agent '{agent_id}' (role={agent_role}) claimed task [{task.get('id')}] "
                f"with --force-role override. Task requires '{required_role}'."
            ),
        }
        with open(INBOX_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "register":
        agent_id = sys.argv[2]
        role = sys.argv[3]
        display = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        try:
            entry = register_agent(agent_id, role, display)
            print(f"Registered '{agent_id}' as role '{role}': {entry}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) >= 2 and sys.argv[1] == "list":
        reg = load_registry()
        if not reg:
            print("Registry is empty")
        else:
            print(f"{'AGENT':<20} {'ROLE':<16} DISPLAY")
            for aid, info in sorted(reg.items()):
                print(f"{aid:<20} {info.get('role','?'):<16} {info.get('display_name','')}")
    else:
        print(__doc__)
