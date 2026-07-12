#!/usr/bin/env python3
"""
Closing Gate V5 — REAL WORK ENFORCEMENT

This gate adds a CRITICAL tier that prevents gaming the system:
- Must prove UNDERSTANDING of task goal (not just passing tests)
- Must prove ACTUAL WORK was done (not fake evidence)
- Must verify work against TASK DESCRIPTION (not just generic checklist)
- Cannot mark done without showing you actually did what was asked

V4 tiers (1-15) still apply, PLUS:
- Tier 16: GOAL_UNDERSTANDING - Must prove you understand what the task asks for
- Tier 17: ACTUAL_WORK - Must prove REAL work, not faked evidence
- Tier 18: GOAL_COMPLETION - Evidence must show you completed the ACTUAL goal stated in task
"""

import sys
from pathlib import Path
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))

from closing_gate_v4 import ClosingGateV4, GateTierV4


class GateTierV5(Enum):
    """V5 Gate tiers (18 total: 15 from V4 + 3 new anti-gaming tiers)"""
    # V4 tiers (1-15)
    VALIDATION = 1
    STATE = 2
    METRIC = 3
    COMPLIANCE = 4
    BEHAVIORAL = 5
    PROGRESSIVE = 6
    DETERMINISTIC = 7
    CRYPTOGRAPHIC = 8
    REALWORLD = 9
    MONITORING = 10
    ROLLBACK = 11
    REVIEW = 12
    ADVERSARIAL = 13
    CERTIFICATION = 14
    ISOLATION = 15
    # V5 anti-gaming tiers (16-18)
    GOAL_UNDERSTANDING = 16  # Must show you understand what task asks for
    ACTUAL_WORK = 17         # Must show real work, not faked evidence
    GOAL_COMPLETION = 18     # Evidence must prove you did what was asked


class ClosingGateV5:
    """Real work enforcement - prevents gaming the system."""

    def __init__(self, task: dict):
        self.task = task
        self.task_id = task.get('id', 'unknown')
        # First run V4 gate
        self.v4_gate = ClosingGateV4(task)
        self.tiers_passed = []
        self.tiers_failed = []

    def validate_all(self) -> dict:
        """Run all 18 tiers. V4 (1-15) THEN V5 (16-18) anti-gaming."""
        # First, run V4
        v4_result = self.v4_gate.validate_all()

        # Track V4 results
        if v4_result['blocked']:
            # If V4 blocks, all V4 tiers blocked
            return {
                'tiers_passed': v4_result['tiers_passed'],
                'tiers_failed': v4_result['tiers_failed'] + 3,  # V5 tiers also fail
                'blocked': True,
                'failures': v4_result['failures'] + [
                    (GateTierV5.GOAL_UNDERSTANDING, 'Cannot verify goal understanding until V4 passes'),
                    (GateTierV5.ACTUAL_WORK, 'Cannot verify actual work until V4 passes'),
                    (GateTierV5.GOAL_COMPLETION, 'Cannot verify goal completion until V4 passes'),
                ]
            }

        # V4 passed, now run V5 anti-gaming tiers
        v5_tiers = [
            (GateTierV5.GOAL_UNDERSTANDING, self.tier_goal_understanding),
            (GateTierV5.ACTUAL_WORK, self.tier_actual_work),
            (GateTierV5.GOAL_COMPLETION, self.tier_goal_completion),
        ]

        v5_failures = []
        for tier, check_func in v5_tiers:
            result = check_func()
            if result['passed']:
                self.tiers_passed.append(tier)
            else:
                self.tiers_failed.append(tier)
                v5_failures.append((tier, result['reason']))

        return {
            'tiers_passed': v4_result['tiers_passed'] + len([t for t in v5_tiers if not any(f[0] == t[0] for f in v5_failures)]),
            'tiers_failed': v4_result['tiers_failed'] + len(v5_failures),
            'blocked': len(v5_failures) > 0,
            'failures': v4_result['failures'] + v5_failures,
        }

    def tier_goal_understanding(self) -> dict:
        """Tier 16: GOAL_UNDERSTANDING - Must prove you understand the task goal."""
        # C-002 FIX: Read from immutable snapshot (_original_description), not mutable field
        # Falls back to 'description' for tasks claimed before this fix
        task_description = str(self.task.get('_original_description') or self.task.get('description', '')).lower()
        evidence = str(self.task.get('evidence', '')).lower()

        if not task_description or len(task_description) < 20:
            return {'passed': False, 'reason': 'GOAL_UNDERSTANDING: Task description missing or too short'}

        # Extract key nouns from task (what needs to be done)
        # Real tasks mention specific things: service names, config files, endpoints, etc.
        description_keywords = task_description.split()

        # Filter for potentially specific terms (not stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'in', 'to', 'with', 'for', 'of', 'on', 'at'}
        specific_terms = [w.strip('.,;:') for w in description_keywords if len(w) > 3 and w.lower() not in stop_words]

        if not specific_terms:
            return {'passed': False, 'reason': 'GOAL_UNDERSTANDING: Task description too generic to understand'}

        # Evidence MUST reference specific terms from task description
        matching_terms = sum(1 for term in specific_terms[:15] if term in evidence)

        if matching_terms < 3:
            return {
                'passed': False,
                'reason': f'GOAL_UNDERSTANDING: Evidence must reference task-specific terms. Task mentions: {", ".join(specific_terms[:5])}, but evidence has <3 matches.'
            }

        return {'passed': True}

    def tier_actual_work(self) -> dict:
        """Tier 17: ACTUAL_WORK - Must prove work was really done, not fabricated."""
        evidence = str(self.task.get('evidence', ''))

        if not evidence or len(evidence) < 150:
            return {'passed': False, 'reason': 'ACTUAL_WORK: Evidence too brief (<150 chars). Provide detailed actual output.'}

        evidence_lower = evidence.lower()

        # REJECT if evidence looks like template/fake (these patterns indicate fake evidence)
        RED_FLAGS = [
            'task completed and deployed',
            'pytest tests passing (exit 0, latency <50ms)',  # Exact template
            'production staging verified (latency p99 <60ms, errors <0.02%, cpu <18%, memory <90mb)',  # Template
            'docker: service running, healthy',  # Generic template
            'systemctl: active and running',  # Generic template
            'git: commit deployed on production',  # Too vague
            'http: curl → http 200 ok',  # Template arrow
            'rollback: instant via git revert tested',  # Generic
            'failure modes: timeout (retry), network (fallback), memory (adaptive)',  # Template list
        ]

        for flag in RED_FLAGS:
            if flag in evidence_lower:
                return {
                    'passed': False,
                    'reason': f'ACTUAL_WORK: Evidence looks like template. Exact phrase found: "{flag}". Describe REAL work, not generic checklist.'
                }

        # REQUIRE real specifics (not templates)
        real_work_indicators = [
            # Actual git commit hashes (8+ hex chars)
            len([c for c in evidence if c in '0123456789abcdef']) >= 10,
            # Actual URLs or IP addresses
            'http://' in evidence or 'localhost:' in evidence or 'prod' in evidence_lower,
            # Actual file paths (/ characters)
            evidence.count('/') >= 3,
            # Actual version numbers (X.X.X)
            '.' in evidence and any(c.isdigit() for c in evidence.split('.')),
            # Actual output/metrics (numbers with units)
            any(f'{n}ms' in evidence or f'{n}mb' in evidence for n in range(10, 200)),
        ]

        if sum(real_work_indicators) < 3:
            return {
                'passed': False,
                'reason': 'ACTUAL_WORK: Evidence lacks real work details (actual hashes, paths, URLs, metrics, versions). Provide actual system output.'
            }

        return {'passed': True}

    def tier_goal_completion(self) -> dict:
        """Tier 18: GOAL_COMPLETION - Evidence must show you completed the ACTUAL goal."""
        task_description = str(self.task.get('description', ''))
        evidence = str(self.task.get('evidence', ''))
        task_title = str(self.task.get('title', ''))

        # Extract what the task ASKS for (imperative verbs)
        ask_keywords = ['deploy', 'build', 'fix', 'implement', 'create', 'test', 'verify', 'update', 'install', 'integrate']
        task_asks_for = [kw for kw in ask_keywords if kw in task_description.lower() or kw in task_title.lower()]

        if not task_asks_for:
            # Task description too unclear
            return {
                'passed': False,
                'reason': 'GOAL_COMPLETION: Task description unclear (missing action verbs like deploy/build/fix). Cannot verify goal was completed.'
            }

        # Evidence must show the ACTUAL action was completed
        # Not just "testing passed" but "deployed to production" or "built X module" etc
        evidence_lower = evidence.lower()
        found_actions = [action for action in task_asks_for if action in evidence_lower]

        if not found_actions:
            return {
                'passed': False,
                'reason': f'GOAL_COMPLETION: Evidence must show you completed the asked-for action. Task asks to: {", ".join(task_asks_for)}'
            }

        return {'passed': True}


def closing_gate_v5(task: dict) -> None:
    """Run V5 closing gate. All 18 tiers must pass. No exceptions."""
    gate = ClosingGateV5(task)
    result = gate.validate_all()

    if result['blocked']:
        failures_str = '\n'.join(
            f"     [{tier.name if hasattr(tier, 'name') else tier:20}] {reason}"
            for tier, reason in result['failures']
        )
        raise ValueError(
            f"\n⛔ CLOSING GATE V5 BLOCKED — {len(result['failures'])} tiers failed\n"
            f"   Task: {task.get('id')} - {task.get('title')}\n"
            f"\n   Failures:\n{failures_str}\n"
            f"\n   Passed: {result['tiers_passed']}/18 tiers"
        )


if __name__ == "__main__":
    # Test V5 gate
    test_task = {
        "id": "TEST-V5",
        "title": "Deploy [Your-AI-Name] authentication service to production",
        "description": """
        Deploy the new authentication service that validates OAuth2 tokens.
        The service should handle token validation with 99.9% uptime SLA.
        Deployment must include: database migration, load balancing, monitoring, and rollback capability.
        """,
        "status": "completed",
        "claimed_at": "2026-07-01T10:00:00Z",
        "completed_at": "2026-07-01T14:00:00Z",
        "evidence": """
        Deployed auth-service v2.1.3 to production cluster.
        Git: commit 8f3c9e2d (auth: Add OAuth2 token validation) merged to main.
        DB: Migration 2026_07_01_0000 applied (token_cache table created with indexes).
        Deployment: Canary rollout to 5% traffic, then 50%, then 100% over 2 hours.
        Testing: OAuth2 token validation tested with 500/500 tokens (99.8% cache hit rate).
        Load test: curl http://api.prod/auth/validate → HTTP 200 OK (45ms p50, 120ms p99).
        Monitoring: Auth latency dashboard shows baseline 35ms→42ms (within SLA).
        Rollback: Tested instant revert via git reset --soft HEAD~1, service restored to v2.1.2 in <2min.
        Uptime: Service ran 4 hours without errors, SLA target: 99.9% (achieved: 99.95%).
        Verified: 2026-07-01T14:15:00Z by integration harness (auth_deploy_verification).
        """,
        "approval_gate_status": "approved",
        "certified_hash": "f3e7d2c1a9b8",
        "memory_recorded": True,
        "advisor_findings": {
            "advisor_id": "adv-auth-v5",
            "approved": True,
            "findings": "OAuth2 pattern follows industry standard, SLA verified"
        }
    }

    try:
        closing_gate_v5(test_task)
        print("✅ Test task PASSED V5 closing gate (all 18 tiers)")
    except ValueError as e:
        print(f"❌ {e}")
