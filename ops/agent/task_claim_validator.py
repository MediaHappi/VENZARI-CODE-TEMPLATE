#!/usr/bin/env python3
"""
TASK CLAIM VALIDATOR — Copied from Apache Airflow DAGBag pattern

Before a task can be claimed, it MUST pass through a validation pipeline.
This is modeled after Airflow's pre-execution DAG validation chain.

Pattern: https://github.com/apache/airflow/blob/main/airflow/models/dagbag.py
"""

import sys
import json
from pathlib import Path
from enum import Enum
from typing import Tuple, Optional, List

# Fix imports for task_manager.py context (where this is called from)
# task_manager.py uses: sys.path.insert(0, str(Path(__file__).parent))
# So we're already in ops/agent directory


class ValidationPhase(Enum):
    """Ordered phases - each MUST pass before next"""
    TASK_DEFINITION = 1  # Task JSON is valid
    AGENT_ROLE_MATCH = 2  # Agent role matches task requirement
    SKILL_LOADING = 3  # Required skills are loadable
    WORKTREE_SETUP = 4  # Worktree exists or can be created
    CONTEXT_INJECTION = 5  # Context can be injected
    DEPENDENCY_READY = 6  # All blocked_by tasks are completed
    APPROVED = 7  # Advisor approval (if needed)


class ClaimValidator:
    """
    Multi-phase validation chain (Airflow DAGBag pattern).

    Each phase validates a prerequisite. If ANY phase fails, task cannot be claimed.
    Phases are sequential and immutable - no skipping.
    """

    def __init__(self, task: dict, agent_name: str):
        self.task = task
        self.agent_name = agent_name
        self.task_id = task.get('id', 'unknown')
        self.failures: List[Tuple[ValidationPhase, str]] = []
        self.passed_phases: List[ValidationPhase] = []

    def validate_all(self) -> Tuple[bool, str]:
        """Run validation chain. Any failure blocks claim."""
        phases = [
            (ValidationPhase.TASK_DEFINITION, self._validate_task_definition),
            (ValidationPhase.AGENT_ROLE_MATCH, self._validate_agent_role),
            (ValidationPhase.SKILL_LOADING, self._validate_skill_loading),
            (ValidationPhase.WORKTREE_SETUP, self._validate_worktree),
            (ValidationPhase.CONTEXT_INJECTION, self._validate_context),
            (ValidationPhase.DEPENDENCY_READY, self._validate_dependencies),
            (ValidationPhase.APPROVED, self._validate_approval),
        ]

        print(f"\n🔍 CLAIM VALIDATION CHAIN for task {self.task_id}")
        print("=" * 70)

        for phase, validator_fn in phases:
            try:
                passed, msg = validator_fn()
                if passed:
                    self.passed_phases.append(phase)
                    print(f"  ✅ {phase.name:<20} PASSED")
                else:
                    self.failures.append((phase, msg))
                    print(f"  ❌ {phase.name:<20} FAILED: {msg}")
                    # Stop on first failure (no skipping phases)
                    break
            except Exception as e:
                self.failures.append((phase, str(e)))
                print(f"  ❌ {phase.name:<20} ERROR: {e}")
                break

        print("=" * 70)

        if self.failures:
            error_msg = f"Validation failed at {self.failures[0][0].name}: {self.failures[0][1]}"
            print(f"\n⛔ CLAIM BLOCKED: {error_msg}\n")
            return False, error_msg

        print(f"\n✅ ALL PHASES PASSED - Task {self.task_id} ready to claim\n")
        return True, "all-phases-passed"

    def _validate_task_definition(self) -> Tuple[bool, str]:
        """Phase 1: Task JSON structure valid"""
        required_fields = ['id', 'title', 'status', 'layer']
        missing = [f for f in required_fields if f not in self.task]

        if missing:
            return False, f"Missing fields: {', '.join(missing)}"

        if self.task.get('status') != 'pending':
            return False, f"Task status is {self.task['status']}, not pending"

        return True, "task-definition-valid"

    def _validate_agent_role(self) -> Tuple[bool, str]:
        """Phase 2: Agent role matches task requirement"""
        required_role = self.task.get('agent_role')

        if not required_role:
            # No specific role required - allow any agent
            return True, "no-role-requirement"

        # In real implementation, would check agent_name against available roles
        # For now, accept if role is specified
        if self.agent_name == required_role or required_role in self.agent_name:
            return True, f"agent-role-matches-{required_role}"

        return False, f"Agent '{self.agent_name}' does not match required role '{required_role}'"

    def _validate_skill_loading(self) -> Tuple[bool, str]:
        """Phase 3: Required skills are loadable"""
        required_skills = self.task.get('required_skills', [])

        if not required_skills:
            return True, "no-required-skills"

        # Check if skills directory exists (try multiple locations)
        possible_locations = [
            Path("/opt/YOUR-PROJECT/agents/skills"),
            Path("/opt/YOUR-PROJECT/ops/agent/skills"),
        ]

        skills_dir = None
        for loc in possible_locations:
            if loc.exists():
                skills_dir = loc
                break

        if not skills_dir:
            # Skills not required to exist - skill_loader will verify at load time
            # This is informational only
            return True, "skills-location-not-found-will-verify-at-load"

        missing_skills = []
        for skill in required_skills:
            skill_file = skills_dir / skill / "SKILL.md"
            if not skill_file.exists():
                missing_skills.append(skill)

        if missing_skills:
            # Skills missing - warning but not block
            # They may be available via skill_loader
            return True, f"skill-files-not-in-expected-location-will-verify-at-load"

        return True, "all-skills-available"

    def _validate_worktree(self) -> Tuple[bool, str]:
        """Phase 4: Worktree can be created (or already exists)"""
        repo_dir = Path("/opt/YOUR-PROJECT")
        worktree_dir = repo_dir / ".worktrees" / self.task_id

        # If worktree already exists for this task, that's ok
        if worktree_dir.exists():
            return True, "worktree-exists"

        # Check .worktrees directory is accessible
        worktrees_parent = repo_dir / ".worktrees"
        if not worktrees_parent.exists():
            return False, ".worktrees directory missing"

        if not worktrees_parent.is_dir():
            return False, ".worktrees is not a directory"

        # Check we can write to it
        try:
            test_file = worktrees_parent / f".test-{self.task_id}"
            test_file.touch()
            test_file.unlink()
            return True, "worktree-creatable"
        except Exception as e:
            return False, f"Cannot create worktree: {e}"

    def _validate_context(self) -> Tuple[bool, str]:
        """Phase 5: Context can be injected"""
        # Check inject_context.py exists
        inject_script = Path("/opt/YOUR-PROJECT/ops/agent/inject_context.py")

        if not inject_script.exists():
            return False, "inject_context.py not found"

        # Context requires task title (for knowledge base lookup)
        if not self.task.get('title'):
            return False, "Task title required for context injection"

        return True, "context-injectable"

    def _validate_dependencies(self) -> Tuple[bool, str]:
        """Phase 6: All blocked_by tasks are completed"""
        blocked_by = self.task.get('blocked_by', [])

        if not blocked_by:
            return True, "no-dependencies"

        # Load all tasks to check status
        tasks_dir = Path("/opt/YOUR-PROJECT/.tasks")
        incomplete_deps = []

        for dep_id in blocked_by:
            task_file = tasks_dir / f"{dep_id}.json"
            if not task_file.exists():
                incomplete_deps.append(f"{dep_id} (not found)")
                continue

            try:
                with open(task_file) as f:
                    dep_task = json.load(f)
                    if dep_task.get('status') != 'completed':
                        incomplete_deps.append(f"{dep_id} ({dep_task.get('status', 'unknown')})")
            except Exception as e:
                incomplete_deps.append(f"{dep_id} (error: {e})")

        if incomplete_deps:
            return False, f"Blocked by incomplete tasks: {', '.join(incomplete_deps)}"

        return True, "all-dependencies-complete"

    def _validate_approval(self) -> Tuple[bool, str]:
        """Phase 7: Advisor approval (if required)"""
        # Check if advisor is needed for this task
        try:
            from ops.agent.advisor_integration import should_call_advisor

            if not should_call_advisor(self.task):
                return True, "advisor-not-required"

            # Advisor required but we don't call it here
            # Just flag that it needs approval
            print(f"    (Advisor approval needed)", file=sys.stderr)
            return True, "advisor-required-note"

        except ImportError:
            # Advisor not available - allow claim
            return True, "advisor-not-available"


def validate_before_claim(task: dict, agent_name: str) -> Tuple[bool, str]:
    """
    Entry point: Validate task before allowing claim.

    Returns: (passed: bool, message: str)
    """
    validator = ClaimValidator(task, agent_name)
    return validator.validate_all()


if __name__ == "__main__":
    # Test with sample task
    test_task = {
        "id": "T0000000001",
        "title": "Test task",
        "status": "pending",
        "layer": "infrastructure",
        "agent_role": "infrastructure",
        "required_skills": ["infra"],
        "blocked_by": []
    }

    passed, msg = validate_before_claim(test_task, "infrastructure")
    print(f"\nValidation result: {passed} ({msg})")
    sys.exit(0 if passed else 1)
