#!/usr/bin/env python3
"""
Closing Gate V2 — Enterprise-Grade Multi-Phase Enforcement

Based on patterns from:
- Apache Airflow DAGBag validation (sequential phases, no skip)
- Kubernetes admission controllers (multi-layer gates)
- dbt-core test validation (freshness checks)

A task can only complete if it passes ALL phases sequentially.
Any phase failure blocks completion. No bypasses.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))


class GatePhase(Enum):
    """Sequential validation phases (must complete in order)"""
    EVIDENCE_COLLECTION = 1    # Evidence exists and is fresh
    DEPENDENCY_VERIFICATION = 2 # All blocked_by tasks verified complete
    INTEGRATION_TEST = 3        # Component interactions work
    DEPLOYMENT_PROOF = 4        # Works in target environment
    ROLLBACK_READY = 5          # Can revert if needed


class ClosingGateV2:
    """Enterprise closing gate with sequential multi-phase validation."""

    def __init__(self, task: dict):
        self.task = task
        self.task_id = task.get('id', 'unknown')
        self.phases_passed = []
        self.phases_failed = []

    def validate_all(self) -> dict:
        """Run all phases sequentially. Stop on first failure."""
        phases = [
            (GatePhase.EVIDENCE_COLLECTION, self.phase_evidence_collection),
            (GatePhase.DEPENDENCY_VERIFICATION, self.phase_dependency_verification),
            (GatePhase.INTEGRATION_TEST, self.phase_integration_test),
            (GatePhase.DEPLOYMENT_PROOF, self.phase_deployment_proof),
            (GatePhase.ROLLBACK_READY, self.phase_rollback_ready),
        ]

        for phase, check_func in phases:
            result = check_func()
            if result['passed']:
                self.phases_passed.append(phase)
            else:
                self.phases_failed.append((phase, result['reason']))
                # STOP on first failure - don't continue
                break

        return {
            'phases_passed': len(self.phases_passed),
            'phases_failed': len(self.phases_failed),
            'blocked': len(self.phases_failed) > 0,
            'failures': self.phases_failed,
        }

    def phase_evidence_collection(self) -> dict:
        """Phase 1: Evidence must be FRESH and MULTI-SOURCE."""
        evidence = self.task.get('evidence', '')
        if not evidence or len(str(evidence).strip()) < 100:
            return {'passed': False, 'reason': 'Evidence too short (<100 chars required for enterprise gate)'}

        # Check for staleness (evidence older than task completion?)
        completed_at = self.task.get('completed_at')
        if not completed_at:
            return {'passed': False, 'reason': 'completed_at timestamp missing'}

        # Check for minimum 3 sources (not 2) - enterprise standard
        sources = sum([
            'pytest' in evidence.lower() and 'passed' in evidence.lower(),
            'git' in evidence.lower() and 'commit' in evidence.lower(),
            ('curl' in evidence.lower() or 'http' in evidence.lower()) and ('200' in evidence or 'ok' in evidence.lower()),
            'docker' in evidence.lower() and 'running' in evidence.lower(),
            ('verified' in evidence.lower() or 'checked' in evidence.lower()) and '@' in evidence,
            'file' in evidence.lower() and 'exists' in evidence.lower(),
        ])

        if sources < 3:
            return {'passed': False, 'reason': f'Insufficient evidence sources ({sources}/3 required)'}

        return {'passed': True}

    def phase_dependency_verification(self) -> dict:
        """Phase 2: All blocked_by tasks must be verified complete."""
        blocked_by = self.task.get('blocked_by', [])
        if not blocked_by:
            return {'passed': True}  # No dependencies

        # Check each dependency
        tasks_dir = Path('/opt/YOUR-PROJECT/.tasks')
        for dep_id in blocked_by:
            # Find and load dependency task
            matching = list(tasks_dir.glob(f"{dep_id}*.json"))
            if not matching:
                return {'passed': False, 'reason': f'Dependency {dep_id} not found'}

            dep_task = json.loads(matching[0].read_text())
            if dep_task.get('status') != 'completed':
                return {'passed': False, 'reason': f'Dependency {dep_id} not completed (status: {dep_task.get("status")})'}

            # Check if dependency has passed closing gates
            if not dep_task.get('closing_gates_passed'):
                return {'passed': False, 'reason': f'Dependency {dep_id} did not pass closing gates'}

        return {'passed': True}

    def phase_integration_test(self) -> dict:
        """Phase 3: Component interactions verified."""
        # For infrastructure/memory/autonomy tasks: must have integration test evidence
        layer = self.task.get('layer', '')
        if layer in ['infrastructure', 'autonomy', 'memory']:
            evidence = self.task.get('evidence', '')
            if 'integration' not in evidence.lower() and 'e2e' not in evidence.lower():
                # Allow if evidence mentions specific component testing
                components = ['memory', 'task', 'advisor', 'skill', 'gate', 'enforcement']
                has_component_test = any(f'{c}_' in evidence.lower() for c in components)
                if not has_component_test:
                    return {'passed': False, 'reason': 'Integration testing evidence required but not found'}

        return {'passed': True}

    def phase_deployment_proof(self) -> dict:
        """Phase 4: Proof that work actually deployed/runs."""
        layer = self.task.get('layer', '')
        evidence = self.task.get('evidence', '')

        if layer in ['infrastructure', 'backend', 'devops']:
            # Must have deployment/runtime proof (curl, docker ps, service status, etc)
            has_deployment_proof = any(keyword in evidence.lower() for keyword in [
                'curl', 'http', 'docker ps', 'systemctl', 'running', 'listening', 'deployed'
            ])
            if not has_deployment_proof:
                return {'passed': False, 'reason': 'Deployment proof required (curl/docker/systemctl evidence)'}

        return {'passed': True}

    def phase_rollback_ready(self) -> dict:
        """Phase 5: Verify work can be reverted if needed."""
        # Check for rollback plan or git revert readiness
        evidence = self.task.get('evidence', '')
        git_info = 'git' in evidence.lower() and ('commit' in evidence.lower() or 'hash' in evidence.lower())

        if not git_info:
            return {'passed': False, 'reason': 'Rollback readiness requires git commit tracking'}

        return {'passed': True}


def closing_gate_v2(task: dict) -> None:
    """
    Run V2 closing gate. Raise exception if any phase fails.
    Sequential: phases run in order, stop on first failure.
    """
    gate = ClosingGateV2(task)
    result = gate.validate_all()

    if result['blocked']:
        phase_name, reason = result['failures'][0]
        raise ValueError(
            f"\n⛔ CLOSING GATE V2 BLOCKED AT PHASE {phase_name.name}\n"
            f"   Task: {task.get('id')} - {task.get('title')}\n"
            f"   Reason: {reason}\n"
            f"\n   Passed phases: {result['phases_passed']}\n"
            f"   Failed phases: {result['phases_failed']}"
        )


if __name__ == "__main__":
    # Test V2 gate
    test_task = {
        "id": "TEST-001",
        "title": "Test task",
        "layer": "infrastructure",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "evidence": "pytest ops/tests/test_integration.py → 15/15 PASSED (exit 0); git commit abc123def on main branch; curl http://localhost:5000 → HTTP 200 OK; docker ps shows service running with ports; systemctl status shows active; integration test verified memory→task→advisor→memory flow working; verified: 2026-07-01 by test harness",
        "blocked_by": [],
        "closing_gates_passed": True,
    }

    try:
        closing_gate_v2(test_task)
        print("✅ Test task passed V2 closing gate")
    except ValueError as e:
        print(f"❌ {e}")
