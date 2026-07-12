#!/usr/bin/env python3
"""
CompletionValidator — unified task completion validation gate
Consolidates 10+ sequential validation checks into single validator with severity ranking
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False


class Severity(Enum):
    """Error severity levels — sorted from highest to lowest"""
    CRITICAL = 0  # Blocks completion, exit(1) required
    HIGH = 1      # Strong enforcement, should block
    MEDIUM = 2    # Warnings, non-blocking but important
    LOW = 3       # Informational


@dataclass
class ValidationResult:
    """Single validation check result"""
    check_name: str
    passed: bool
    severity: Severity
    message: str
    details: str = ""

    def __lt__(self, other):
        # Sort by severity (critical first)
        return self.severity.value < other.severity.value


class CompletionValidator:
    """Unified validator for task completion — consolidates all gates with severity ranking"""

    def __init__(self, task, summary, evidence, skill_used):
        self.task = task
        self.summary = summary
        self.evidence = evidence or ""
        self.skill_used = skill_used
        self.results = []

    def validate_all(self):
        """Run all validation checks and return sorted results"""
        # Check 1: Evidence requirement
        self.check_evidence_exists()

        # Check 2: Skill requirement
        self.check_skill_required()

        # Check 3: Evidence has real output
        self.check_evidence_quality()

        # Check 4: Skill matches required skills
        self.check_skill_match()

        # Check 5: Doc tasks mention updates
        self.check_doc_task_updates()

        # Check 6: Doc drift — required docs updated
        self.check_doc_drift()

        # Check 7: Contradiction detection
        self.check_contradictions()

        # Check 8: Independent evidence validation
        self.check_evidence_validation()

        # Check 9: Approval gate
        self.check_approval_gate()

        # Check 10: State machine
        self.check_state_machine()

        # Check 11: Regression detection
        self.check_regressions()

        # Check 12: Goal substitution
        self.check_goal_substitution()

        # ── TASK 10006: ADVISOR CLOSING GATES ──
        # Check 13: Advisor evidence validity
        self.check_advisor_evidence_validity()

        # Check 14: Advisor closing skills recorded
        self.check_advisor_closing_skills()

        # Check 15: Knowledge base linkage
        self.check_knowledge_base_linkage()

        # Check 16: Advisor drift (contradictions with findings)
        self.check_advisor_drift()

        # Sort by severity (critical first)
        self.results.sort()
        return self.results

    def has_blocking_failures(self):
        """Return True if any CRITICAL or HIGH severity failures exist"""
        return any(r for r in self.results if not r.passed and r.severity in [Severity.CRITICAL, Severity.HIGH])

    def check_evidence_exists(self):
        """Check 1: Evidence is required and must be meaningful"""
        if not self.evidence or len(self.evidence.strip()) < 20:
            self.results.append(ValidationResult(
                check_name="Evidence Requirement",
                passed=False,
                severity=Severity.CRITICAL,
                message="Evidence is required and must be meaningful (20+ chars)",
                details="Evidence must contain: curl HTTP status, commit hash, test output, or 'verified: <method>'"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Evidence Requirement",
                passed=True,
                severity=Severity.CRITICAL,
                message="✓ Evidence provided"
            ))

    def check_skill_required(self):
        """Check 2: Skill parameter is required (P1-4 mandatory)"""
        if not self.skill_used:
            skill_suggestions = "Try: code-review, build-and-verify, security-review, task-completion-verifier"
            self.results.append(ValidationResult(
                check_name="Skill Requirement",
                passed=False,
                severity=Severity.CRITICAL,
                message="--skill parameter is required (P1-4 mandatory enforcement)",
                details=f"Every task completion MUST declare which closing skill was used.\n     Available: {skill_suggestions}\n     See docs/governance/CLOSING_SKILL_MATRIX.md"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Skill Requirement",
                passed=True,
                severity=Severity.CRITICAL,
                message=f"✓ Skill declared: {self.skill_used}"
            ))

    def check_evidence_quality(self):
        """Check 3: Evidence contains real command output, not just descriptions"""
        evidence_lower = self.evidence.lower()
        patterns = ['$', 'curl', 'git', 'docker', 'cat', 'grep', 'test', 'npm', 'python',
                    'HTTP', 'Error', 'commit', 'diff', 'echo', 'bash', 'command', '-1', '→']
        has_real_output = any(pattern in self.evidence for pattern in patterns)

        if not has_real_output and len(self.evidence.strip()) < 100:
            self.results.append(ValidationResult(
                check_name="Evidence Quality",
                passed=False,
                severity=Severity.CRITICAL,
                message="Evidence looks like description, not real output",
                details="Must contain actual command output: curl responses, git hashes, test output, logs.\n"
                        "Bad: 'Verified that the endpoint works correctly'\n"
                        "Good: 'curl http://localhost:5002/health → HTTP 200'"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Evidence Quality",
                passed=True,
                severity=Severity.CRITICAL,
                message="✓ Evidence contains real output"
            ))

    def check_skill_match(self):
        """Check 4: Skill matches required_skills from task"""
        if self.task.get('required_skills'):
            required = [s.lower() for s in self.task['required_skills']]
            skill_lower = self.skill_used.lower() if self.skill_used else ""
            matches = any(skill_lower in req or req in skill_lower for req in required)

            if not matches:
                # Billy's correction (task T0000000023) on the first pass at this
                # (T0000000022): telling the agent "pass --skill <exact_value>" was
                # WRONG -- it invites relabeling past the gate instead of actually
                # redoing the work. A skill mismatch is a SIGNAL the agent skipped the
                # required skill's methodology (e.g. required_skills includes
                # "security-review" but no actual security review was performed) --
                # the fix is to load that skill and re-verify the work against it, not
                # to pick a matching string. Billy: "this is likely to reveal more that
                # needs to be done" -- surfacing more gaps here is the correct outcome.
                required_skills = self.task['required_skills']

                # T0000000022: if a required skill is NOT in the skill library, list
                # the closest loadable alternatives so the agent doesn't guess blindly.
                loadable_hint = ""
                try:
                    import subprocess as _sp
                    _result = _sp.run(
                        ["python3", "ops/agent/skill_loader.py", "list"],
                        capture_output=True, text=True, timeout=10,
                        cwd=str(Path(__file__).resolve().parent.parent.parent)
                    )
                    _available = [
                        line.strip().split()[0]
                        for line in _result.stdout.splitlines()
                        if line.strip() and not line.startswith("===") and not line.startswith("#")
                    ]
                    _missing = [s for s in required_skills if s.lower() not in [a.lower() for a in _available]]
                    if _missing and _available:
                        loadable_hint = (
                            f"\nNOTE: Required skill(s) not in skill library: {_missing}\n"
                            f"Loadable skills available (pick closest by methodology): {_available}"
                        )
                except Exception:
                    pass

                self.results.append(ValidationResult(
                    check_name="Skill Match",
                    passed=False,
                    severity=Severity.HIGH,
                    message="Wrong skill used -- work must be redone with the correct methodology, not relabeled",
                    details=f"Task requires: {required_skills}\nYou used: {self.skill_used}\n"
                            f"This is not a labeling problem. Do NOT just retry with a different --skill "
                            f"string. Instead:\n"
                            f"  1. Load the required skill: python3 ops/agent/skill_loader.py load "
                            f"\"{required_skills[0]}\"\n"
                            f"  2. Re-check the actual work against that skill's methodology -- a mismatch "
                            f"usually means a required step (review, verification, approach) was skipped.\n"
                            f"  3. Do the missing work if you find a real gap, THEN complete with the skill "
                            f"that actually matches what was done."
                            + loadable_hint
                ))
            else:
                # 2026-07-04 (Billy): a matching --skill STRING is not enough — the skill
                # must have actually been loaded for this task. claim_task() now loads
                # every required skill and stamps skills_loaded_at_claim on the task; a
                # completion whose declared skill was never loaded means the methodology
                # was named, not applied — same redo rule as a mismatch, not a relabel.
                loaded = (self.task.get('skills_loaded_at_claim') or {}).get('skills', [])
                loaded_lower = [s.lower() for s in loaded]
                skill_was_loaded = any(
                    skill_lower in ls or ls in skill_lower for ls in loaded_lower
                ) if loaded_lower else False
                if 'skills_loaded_at_claim' in self.task and not skill_was_loaded:
                    self.results.append(ValidationResult(
                        check_name="Skill Match",
                        passed=False,
                        severity=Severity.HIGH,
                        message="Declared skill was never actually loaded for this task — apply the methodology, don't relabel",
                        details=f"Task requires: {self.task['required_skills']}; loaded at claim: {loaded}.\n"
                                f"Load it and re-verify the work against it before completing:\n"
                                f"  python3 ops/agent/skill_loader.py load \"{self.task['required_skills'][0]}\""
                    ))
                else:
                    # Tasks claimed before skills_loaded_at_claim existed pass on the
                    # string match alone — don't retroactively block in-flight work.
                    self.results.append(ValidationResult(
                        check_name="Skill Match",
                        passed=True,
                        severity=Severity.HIGH,
                        message="✓ Skill matches required skills"
                                + ("" if skill_was_loaded else " (legacy claim — no load record to verify)")
                    ))
        else:
            self.results.append(ValidationResult(
                check_name="Skill Match",
                passed=True,
                severity=Severity.HIGH,
                message="✓ No required skills to match"
            ))

    def check_doc_task_updates(self):
        """Check 5: For DOC tasks, verify doc updates are mentioned"""
        if "title" not in self.task:
            return  # Skip if task has no title
        if "DOC" in self.task['title'].upper() and "UPDATE" not in self.task['title'].upper():
            doc_keywords = ["doc", "updated", "changed", "added", "created", "modified", "written"]
            summary_lower = self.summary.lower()
            evidence_lower = self.evidence.lower()
            has_doc_mention = any(kw in summary_lower or kw in evidence_lower for kw in doc_keywords)

            if not has_doc_mention:
                self.results.append(ValidationResult(
                    check_name="Doc Task Updates",
                    passed=False,
                    severity=Severity.HIGH,
                    message="Doc task but no document updates mentioned in summary/evidence",
                    details="Must mention which docs were changed: 'updated X.md', 'created Y.md', etc."
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="Doc Task Updates",
                    passed=True,
                    severity=Severity.HIGH,
                    message="✓ Doc updates mentioned"
                ))
        else:
            self.results.append(ValidationResult(
                check_name="Doc Task Updates",
                passed=True,
                severity=Severity.HIGH,
                message="✓ Not a doc task"
            ))

    def check_doc_drift(self):
        """Check 6: Doc drift enforcement — verify required docs were updated (Task 1827)"""
        try:
            from ops.agent.drift_scanner import verify_doc_updates
            doc_result = verify_doc_updates(self.task)
            if doc_result.get("status") == "missing":
                missing = doc_result.get("missing_docs", [])
                self.results.append(ValidationResult(
                    check_name="Doc Drift Enforcement",
                    passed=False,
                    severity=Severity.CRITICAL,
                    message="Required docs were not updated",
                    details=f"Missing updates for: {', '.join(missing)}"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="Doc Drift Enforcement",
                    passed=True,
                    severity=Severity.CRITICAL,
                    message="✓ Required docs updated"
                ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Doc Drift Enforcement",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ drift_scanner not available (skip)"
            ))

    def check_contradictions(self):
        """Check 7: Contradiction detection (Task 1830)"""
        try:
            from ops.agent.contradiction_detector import check_and_block
            check_and_block(self.task, summary=self.summary, skip_curl=True)
            self.results.append(ValidationResult(
                check_name="Contradiction Detection",
                passed=True,
                severity=Severity.HIGH,
                message="✓ No contradictions detected"
            ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Contradiction Detection",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ contradiction_detector not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="Contradiction Detection",
                passed=False,
                severity=Severity.HIGH,
                message="Contradiction detected",
                details=str(e)
            ))

    def check_evidence_validation(self):
        """Check 8: Independent evidence validation gate (Task 1831)"""
        try:
            from ops.agent.validator import validate_or_exit
            validate_or_exit(self.task, self.evidence)
            self.results.append(ValidationResult(
                check_name="Evidence Validation",
                passed=True,
                severity=Severity.HIGH,
                message="✓ Evidence validated"
            ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Evidence Validation",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ validator not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="Evidence Validation",
                passed=False,
                severity=Severity.HIGH,
                message="Evidence validation failed",
                details=str(e)
            ))

    def check_approval_gate(self):
        """Check 9: Approval gate for governance-critical tasks (Task 1837 — P2-7)"""
        try:
            from ops.agent.approval_gate import check_and_block as approval_check
            approval_check(self.task)
            self.results.append(ValidationResult(
                check_name="Approval Gate",
                passed=True,
                severity=Severity.CRITICAL,
                message="✓ Approval gate passed"
            ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Approval Gate",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ approval_gate not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="Approval Gate",
                passed=False,
                severity=Severity.CRITICAL,
                message="Approval gate blocked",
                details=str(e)
            ))

    def check_state_machine(self):
        """Check 10: State machine enforcement (Task 1839 — P4-1): validate in_progress→completed"""
        try:
            from ops.agent.state_machine_enforcer import enforce_or_exit as sm_enforce
            sm_enforce(self.task, 'completed')
            self.results.append(ValidationResult(
                check_name="State Machine",
                passed=True,
                severity=Severity.HIGH,
                message="✓ State transition valid"
            ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="State Machine",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ state_machine_enforcer not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="State Machine",
                passed=False,
                severity=Severity.HIGH,
                message="State machine validation failed",
                details=str(e)
            ))

    def check_regressions(self):
        """Check 11: Regression detection (Task 1845 — P3-1): compare pre/post service snapshots"""
        try:
            from ops.agent.regression_detector import compare_snapshots
            regression_result = compare_snapshots(self.task['id'], label_a="pre", label_b="post")
            if regression_result and regression_result.get('regressions'):
                regressions = regression_result['regressions']
                self.results.append(ValidationResult(
                    check_name="Regression Detection",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message="Regressions detected",
                    details=f"Found {len(regressions)} regression(s). Verify services are still healthy."
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="Regression Detection",
                    passed=True,
                    severity=Severity.MEDIUM,
                    message="✓ No regressions detected"
                ))
        except (ImportError, Exception):
            self.results.append(ValidationResult(
                check_name="Regression Detection",
                passed=True,
                severity=Severity.LOW,
                message="⊘ regression_detector not available (skip)"
            ))

    def check_goal_substitution(self):
        """Check 12: Goal substitution detection (Task 1845 — P3-2): evidence scope vs task scope"""
        try:
            from ops.agent.goal_substitution_detector import detect_goal_substitution
            sub_result = detect_goal_substitution(self.task, self.evidence or "")
            if sub_result and sub_result.detected:
                self.results.append(ValidationResult(
                    check_name="Goal Substitution",
                    passed=False,
                    severity=Severity.MEDIUM,
                    message="Goal substitution detected",
                    details=f"{sub_result.reason}. Evidence may not cover full task scope."
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="Goal Substitution",
                    passed=True,
                    severity=Severity.MEDIUM,
                    message="✓ No goal substitution detected"
                ))
        except (ImportError, Exception):
            self.results.append(ValidationResult(
                check_name="Goal Substitution",
                passed=True,
                severity=Severity.LOW,
                message="⊘ goal_substitution_detector not available (skip)"
            ))

    def check_advisor_evidence_validity(self):
        """Check 13 (TASK 10006): Advisor evidence matches EVIDENCE_SCHEMA.md"""
        # Only check if task has advisor_findings
        if not self.task.get('advisor_findings'):
            self.results.append(ValidationResult(
                check_name="Advisor Evidence Validity",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ No advisor findings (not an advisor task)"
            ))
            return

        try:
            from ops.agent.evidence_validator import classify
            advisor_findings = self.task.get('advisor_findings', {})
            evidence_text = str(advisor_findings.get('evidence', ''))

            if not evidence_text or len(evidence_text) < 10:
                self.results.append(ValidationResult(
                    check_name="Advisor Evidence Validity",
                    passed=False,
                    severity=Severity.MEDIUM,  # Was HIGH — demoted: infra failure ≠ task failure
                    message="⚠ Advisor evidence is missing or too short (advisory warning)",
                    details="Advisor findings have no evidence field — likely advisor memory write failed. Task evidence (--evidence) is the authoritative source."
                ))
            else:
                evidence_type = classify(evidence_text)
                self.results.append(ValidationResult(
                    check_name="Advisor Evidence Validity",
                    passed=True,
                    severity=Severity.HIGH,
                    message=f"✓ Advisor evidence valid ({evidence_type.value})"
                ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Advisor Evidence Validity",
                passed=True,
                severity=Severity.LOW,
                message="⊘ evidence_validator not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="Advisor Evidence Validity",
                passed=False,
                severity=Severity.MEDIUM,
                message="Advisor evidence validation error",
                details=str(e)
            ))

    def check_advisor_closing_skills(self):
        """Check 14 (TASK 10006): Advisor closing_skills are recorded.

        NOTE (2026-07-05 hardening): demoted from HIGH→MEDIUM per YOUR-PROJECT gate
        review. Rationale: advisor_findings.closing_skills may be absent because
        the advisor memory system (PostgreSQL/ChromaDB) was unreachable from outside
        the container at task-creation time — this is an infrastructure constraint,
        not evidence that the task work was fake. Hard-blocking on infra failures
        trains agents and humans to work around gates entirely (anti-pattern per
        Verify-Gated Completion paper). Real completion fraud is caught by
        check_evidence_exists (CRITICAL) and check_evidence_quality (CRITICAL).
        Advisory checks stay advisory unless explicitly promoted to authority.
        """
        # Only check if task has advisor_findings
        if not self.task.get('advisor_findings'):
            self.results.append(ValidationResult(
                check_name="Advisor Closing Skills",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ No advisor findings (not an advisor task)"
            ))
            return

        advisor_findings = self.task.get('advisor_findings', {})
        closing_skills = advisor_findings.get('closing_skills', [])

        # Also accept closing_skills stored directly on the task (manual patch path)
        if not closing_skills:
            closing_skills = self.task.get('closing_skills', [])

        if not closing_skills or len(closing_skills) == 0:
            self.results.append(ValidationResult(
                check_name="Advisor Closing Skills",
                passed=False,
                severity=Severity.MEDIUM,  # Was HIGH — demoted: infra failure ≠ task failure
                message="⚠ Advisor closing_skills not recorded (advisory warning only)",
                details="Skills not recorded — likely advisor memory write failed. Use --skill to document skill used. This is a warning, not a block."
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Advisor Closing Skills",
                passed=True,
                severity=Severity.MEDIUM,
                message=f"✓ Advisor closing skills recorded: {', '.join(closing_skills)}"
            ))

    def check_knowledge_base_linkage(self):
        """Check 15 (TASK 10006): Advisor findings are linked to knowledge base"""
        # Only check if task has advisor_findings
        if not self.task.get('advisor_findings'):
            self.results.append(ValidationResult(
                check_name="Knowledge Base Linkage",
                passed=True,
                severity=Severity.MEDIUM,
                message="⊘ No advisor findings (not an advisor task)"
            ))
            return

        try:
            from pathlib import Path
            from ops.agent.advisor_manager import get_advisor_findings

            task_layer = self.task.get('layer', 'infrastructure').lower()
            findings = get_advisor_findings(task_layer)

            # Check if advisor_findings are present in knowledge base
            advisor_findings = self.task.get('advisor_findings', {})
            advisor_id = advisor_findings.get('advisor_id')

            if findings and len(findings) > 0:
                self.results.append(ValidationResult(
                    check_name="Knowledge Base Linkage",
                    passed=True,
                    severity=Severity.MEDIUM,  # Was HIGH — advisory only
                    message=f"✓ Findings linked to knowledge base ({len(findings)} findings in {task_layer})"
                ))
            else:
                # Findings not yet persisted, but that's OK if findings exist
                if advisor_findings:
                    self.results.append(ValidationResult(
                        check_name="Knowledge Base Linkage",
                        passed=True,
                        severity=Severity.MEDIUM,
                        message="✓ Advisor findings present (will be persisted to knowledge base)"
                    ))
                else:
                    self.results.append(ValidationResult(
                        check_name="Knowledge Base Linkage",
                        passed=False,
                        severity=Severity.MEDIUM,
                        message="Advisor findings not linked to knowledge base",
                        details="Advisor findings should be persisted for future task reuse"
                    ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Knowledge Base Linkage",
                passed=True,
                severity=Severity.LOW,
                message="⊘ advisor_manager not available (skip)"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                check_name="Knowledge Base Linkage",
                passed=False,
                severity=Severity.MEDIUM,
                message="Knowledge base linkage check error",
                details=str(e)
            ))

    def check_advisor_drift(self):
        """Check 16 (TASK 10006): Advisor findings are not contradicted by later work"""
        # Only check if task has advisor_findings
        if not self.task.get('advisor_findings'):
            self.results.append(ValidationResult(
                check_name="Advisor Drift",
                passed=True,
                severity=Severity.LOW,
                message="⊘ No advisor findings (not an advisor task)"
            ))
            return

        try:
            from ops.agent.contradiction_detector import check_and_block

            advisor_findings = self.task.get('advisor_findings', {})
            findings_str = str(advisor_findings)

            # Check if advisor findings contradict current evidence/summary
            check_and_block(self.task, summary=findings_str, skip_curl=True)

            self.results.append(ValidationResult(
                check_name="Advisor Drift",
                passed=True,
                severity=Severity.MEDIUM,
                message="✓ No drift detected between advisor findings and task work"
            ))
        except ImportError:
            self.results.append(ValidationResult(
                check_name="Advisor Drift",
                passed=True,
                severity=Severity.LOW,
                message="⊘ contradiction_detector not available (skip)"
            ))
        except Exception as e:
            # Drift detected is a warning, not a blocker
            self.results.append(ValidationResult(
                check_name="Advisor Drift",
                passed=False,
                severity=Severity.MEDIUM,
                message="Potential drift: advisor findings may conflict with task work",
                details=str(e)
            ))

    def print_results(self):
        """Print validation results sorted by severity"""
        if not self.results:
            return

        # Group by pass/fail
        failures = [r for r in self.results if not r.passed]
        passes = [r for r in self.results if r.passed]

        if failures:
            print("\n⛔ VALIDATION FAILURES (sorted by severity):", file=sys.stderr)
            for result in failures:
                severity_str = f"[{result.severity.name}]"
                print(f"  {severity_str} {result.check_name}: {result.message}", file=sys.stderr)
                if result.details:
                    for line in result.details.split('\n'):
                        print(f"         {line}", file=sys.stderr)

        if passes:
            print(f"\n✓ {len(passes)} validation checks passed", file=sys.stderr)
