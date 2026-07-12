#!/usr/bin/env python3
"""
Advanced typed closing gate base for YOUR-PROJECT.

Design goals:
- per-layer gates stay specific but share one strict execution contract
- no shell bypasses such as "|| true"
- evidence requirements are enforced, not just declared
- checks adapt to changed files and existing test targets
- failure messages tell the agent what to fix next
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class CommandCheck:
    name: str
    argv: Sequence[str]
    reason: str
    required: bool = True
    timeout: int = 120
    run_if_files_exist: Sequence[str] = field(default_factory=tuple)
    run_if_any_changed_prefix: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvidenceRule:
    name: str
    description: str
    keywords_any: Sequence[str] = field(default_factory=tuple)
    keywords_all: Sequence[str] = field(default_factory=tuple)
    patterns: Sequence[str] = field(default_factory=tuple)
    required: bool = True


@dataclass
class CheckResult:
    check_name: str
    passed: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class GateResult:
    passed: bool
    layer: str
    task_id: str
    checks_passed: int
    checks_failed: int
    failures: List[tuple[str, str]]
    check_results: List[CheckResult]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseGate:
    layer_slug = "uncategorized"

    def __init__(self, task: dict):
        self.task = task
        self.task_id = task.get("id") or task.get("task_id") or "unknown"
        self.layer = task.get("layer", self.layer_slug)
        self.description = task.get("_original_description") or task.get("description", "")
        self.evidence = self._collect_evidence(task)
        self.dod = task.get("dod") or task.get("acceptance_criteria") or []

    def required_executable_checks(self) -> List[CommandCheck]:
        return default_checks_for_layer(self.layer_slug, self.changed_files())

    def evidence_requirements(self) -> List[EvidenceRule]:
        return default_evidence_for_layer(self.layer_slug)

    def mandatory_test_command(self) -> List[CommandCheck]:
        return default_test_checks_for_layer(self.layer_slug, self.changed_files())

    def changed_files(self) -> list[str]:
        names = set()
        for argv in (
            ["git", "diff", "--name-only", "HEAD^", "HEAD"],
            ["git", "diff", "--name-only", "--cached"],
            ["git", "diff", "--name-only"],
        ):
            proc = subprocess.run(argv, cwd=REPO, text=True, capture_output=True)
            if proc.returncode == 0:
                names.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
        return sorted(names)

    def validate_all(self) -> GateResult:
        failures: list[tuple[str, str]] = []
        results: list[CheckResult] = []

        for check in self._normalize_checks(self.required_executable_checks() + self.mandatory_test_command()):
            result = self._run_check(check)
            results.append(result)
            if not result.passed and check.required:
                failures.append((check.name, self._failure_reason(check, result)))

        for rule in self.evidence_requirements():
            ok, reason = self._validate_evidence(rule)
            if not ok:
                failures.append((f"evidence:{rule.name}", reason))

        policy_failures = self._static_policy_failures()
        failures.extend(policy_failures)

        return GateResult(
            passed=not failures,
            layer=self.layer,
            task_id=self.task_id,
            checks_passed=sum(1 for r in results if r.passed or r.skipped),
            checks_failed=len(failures),
            failures=failures,
            check_results=results,
        )

    def format_failure_message(self, result: GateResult) -> str:
        lines = [
            f"\nBLOCKED: {self.layer.upper()} typed closing gate failed",
            f"Task: {result.task_id}",
            f"Passed executable checks: {result.checks_passed}/{len(result.check_results)}",
            "",
            "Fix these before completing the task:",
        ]
        for name, reason in result.failures:
            lines.append(f"- {name}: {reason}")
        lines.append("")
        lines.append("Do not weaken or bypass the gate. Add the missing implementation, tests, docs, or evidence.")
        return "\n".join(lines)

    def _collect_evidence(self, task: dict) -> str:
        parts = [str(task.get("evidence", "")), str(task.get("completion_notes", ""))]
        for item in task.get("evidence_log", []) or []:
            parts.append(str(item))
        for item in task.get("dod", []) or []:
            parts.append(str(item))
        return "\n".join(part for part in parts if part)

    def _normalize_checks(self, checks: Iterable[CommandCheck | str]) -> list[CommandCheck]:
        normalized = []
        for check in checks:
            if isinstance(check, CommandCheck):
                normalized.append(check)
            else:
                normalized.append(CommandCheck(name=str(check).split()[0], argv=shlex.split(str(check)), reason="legacy check"))
        return normalized

    def _run_check(self, check: CommandCheck) -> CheckResult:
        command = " ".join(shlex.quote(str(part)) for part in check.argv)
        bypass_tokens = ("||", "&& true", "; true", "| true")
        if any(token in command for token in bypass_tokens):
            return CheckResult(check.name, False, command, 126, "", "gate command contains bypass token")

        # Re-entrancy guard (task T0000000024): a gate check that shells out to
        # `pytest ops/tests/` (the testing layer's full-suite check, or any
        # pytest_check()-generated selector check) will, if invoked from a test
        # that itself calls task_manager.py complete, re-collect and re-run the
        # SAME test -- which calls complete again, which runs the gate again,
        # which runs pytest again. Confirmed live during task S0000000003:
        # test_completion_ownership.py's subprocess calls to `complete` triggered
        # exactly this, producing 77+ concurrent pytest/task_manager processes and
        # a system load average of 22.67 on a 6-core machine before being killed.
        # PYTEST_CURRENT_TEST is set automatically by pytest for the duration of
        # every test -- if it's set AND this check would itself invoke pytest,
        # skip rather than recurse. The outer pytest run already covers this.
        if os.environ.get("PYTEST_CURRENT_TEST") and "pytest" in check.argv:
            return CheckResult(
                check.name, True, command, 0, "", "",
                skipped=True,
                skip_reason="skipped: already running inside pytest (PYTEST_CURRENT_TEST set) -- "
                             "running pytest from a gate check invoked by a test would recurse",
            )

        for path in check.run_if_files_exist:
            if not (REPO / path).exists():
                return CheckResult(check.name, True, command, 0, "", "", skipped=True, skip_reason=f"missing optional target {path}")

        changed = self.changed_files()
        if check.run_if_any_changed_prefix and not any(
            any(path.startswith(prefix) for prefix in check.run_if_any_changed_prefix)
            for path in changed
        ):
            return CheckResult(check.name, True, command, 0, "", "", skipped=True, skip_reason="no matching changed files")

        try:
            proc = subprocess.run(check.argv, cwd=REPO, text=True, capture_output=True, timeout=check.timeout)
            return CheckResult(check.name, proc.returncode == 0, command, proc.returncode, proc.stdout[-4000:], proc.stderr[-4000:])
        except subprocess.TimeoutExpired as exc:
            return CheckResult(check.name, False, command, -1, exc.stdout or "", f"timed out after {check.timeout}s")

    def _failure_reason(self, check: CommandCheck, result: CheckResult) -> str:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.exit_code}"
        return f"{check.reason}. Command `{result.command}` failed: {detail[-1200:]}"

    def _validate_evidence(self, rule: EvidenceRule) -> tuple[bool, str]:
        if not rule.required:
            return True, ""
        text = (self.evidence + "\n" + self.description).lower()
        missing_all = [kw for kw in rule.keywords_all if kw.lower() not in text]
        if missing_all:
            return False, f"{rule.description}; missing required words: {', '.join(missing_all)}"
        if rule.keywords_any and not any(kw.lower() in text for kw in rule.keywords_any):
            return False, f"{rule.description}; needs one of: {', '.join(rule.keywords_any)}"
        for pattern in rule.patterns:
            if not re.search(pattern, self.evidence + "\n" + self.description, re.I | re.M):
                return False, f"{rule.description}; missing pattern: {pattern}"
        return True, ""

    def _static_policy_failures(self) -> list[tuple[str, str]]:
        failures: list[tuple[str, str]] = []
        changed = self.changed_files()
        # base_gate.py itself legitimately contains the strings "|| true" and "shell=True"
        # as detection literals (this very check) and in its own docstring -- without this
        # exclusion, any future edit to base_gate.py would self-flag as violating its own
        # policy, making the shared gate contract effectively unmodifiable. Found via a
        # real test failure during task T0000000020's installation, not a hypothetical.
        gate_files = [
            p for p in changed
            if p.startswith("ops/agent/gates/") and p != "ops/agent/gates/base_gate.py"
        ]
        for rel in gate_files:
            path = REPO / rel
            if path.exists():
                text = path.read_text(errors="ignore")
                if "|| true" in text:
                    failures.append(("policy:no-bypass", f"{rel} contains `|| true`; gates must fail honestly"))
                if "shell=True" in text:
                    failures.append(("policy:no-shell-true", f"{rel} uses shell=True; use argv commands unless explicitly justified"))
        for rel in changed:
            path = REPO / rel
            if path.suffix == ".md" and path.exists():
                text = path.read_text(errors="ignore")
                if "<<<<<<<" in text or ">>>>>>>" in text:
                    failures.append(("policy:no-conflict-markers", f"{rel} still has merge conflict markers"))
        return failures


def existing(paths: Sequence[str]) -> list[str]:
    return [p for p in paths if (REPO / p).exists()]


def pytest_check(name: str, selector: str, reason: str, *, required: bool = True) -> CommandCheck:
    return CommandCheck(name=name, argv=["python3", "-m", "pytest", "ops/tests/", "-q", "-k", selector], reason=reason, required=required, timeout=240)


def default_checks_for_layer(layer: str, changed: Sequence[str]) -> list[CommandCheck]:
    checks = [
        CommandCheck("git-head-exists", ["git", "rev-parse", "HEAD"], "repo must have a valid HEAD"),
        # Precise 7-char marker match (not followed by an 8th of the same char) so
        # decorative "====...====" separator lines (found in real docs/scripts, e.g.
        # docs/CRITICAL_AUDIT_FINDINGS-2026-06-27.md) don't false-positive as conflict
        # markers -- found via a real gate failure during task T0000000020.
        CommandCheck("no-conflict-markers", ["bash", "-lc", "grep -RIn -E '^(<{7}([^<]|$)|={7}([^=]|$)|>{7}([^>]|$))' -- CLAUDE.md GOLDEN_RULES.md docs system-map ops 2>/dev/null; test $? -eq 1"], "no unresolved conflict markers may remain", timeout=60),
    ]
    # Compile exactly the changed .py files the gate itself detected (`changed` is the
    # union of last-commit + staged + working-tree diffs). The old command re-derived the
    # list from `git diff HEAD^ HEAD` only — whenever the last commit was docs-only but
    # working-tree/staged changes included .py files, the shell substitution expanded to
    # NOTHING and py_compile exited 2 with "filenames required", blocking EVERY layer's
    # closing gate for reasons unrelated to the task (found 2026-07-04 via a dry-run of
    # the gates against real pending tasks). Deleted files are skipped — they can't and
    # needn't compile.
    py_changed = [p for p in changed if p.endswith(".py") and (REPO / p).exists()]
    if py_changed:
        checks.append(CommandCheck("python-compile-changed", ["python3", "-m", "py_compile", *py_changed], "changed Python files must compile", timeout=120))
    if any(p.startswith("docs/") or p.endswith(".md") for p in changed):
        checks.append(CommandCheck("doc-template-frontmatter", ["python3", "-m", "pytest", "ops/tests/test_current_state_frontmatter_check.py", "-q"], "doc template/frontmatter checks must pass", required=False, run_if_files_exist=("ops/tests/test_current_state_frontmatter_check.py",), timeout=120))
        checks.append(CommandCheck("wiki-format", ["python3", "-m", "pytest", "ops/tests/test_wiki_human_readable_format.py", "-q"], "human-readable wiki format checks must pass", required=False, run_if_files_exist=("ops/tests/test_wiki_human_readable_format.py",), timeout=120))

    layer_specific = {
        "security": [pytest_check("security-tests", "security or approval or gate", "security-sensitive work needs targeted tests")],
        "memory": [pytest_check("memory-tests", "memory or chroma or redis or durable", "memory work needs persistence/durability tests")],
        "infrastructure": [pytest_check("infra-tests", "infrastructure or gate or registry or task_manager", "infrastructure work needs task/system tests")],
        "documentation": [pytest_check("documentation-tests", "documentation or wiki or current_state", "documentation work needs doc/wiki tests", required=False)],
        "testing": [CommandCheck("full-ops-tests", ["python3", "-m", "pytest", "ops/tests/", "-q"], "testing-layer work must not regress existing ops tests", timeout=420)],
        "training": [pytest_check("training-tests", "training or pipeline or model", "training work needs pipeline/model tests", required=False)],
        "orchestration": [pytest_check("orchestration-tests", "orchestration or advisor or task_manager or inject_context", "orchestration work needs routing/advisor tests")],
    }
    checks.extend(layer_specific.get(layer, [pytest_check(f"{layer}-smoke-tests", layer, f"{layer} work needs targeted tests", required=False)]))
    return checks


def default_test_checks_for_layer(layer: str, changed: Sequence[str]) -> list[CommandCheck]:
    test_files = [p for p in changed if p.startswith("ops/tests/") and p.endswith(".py")]
    if test_files:
        return [CommandCheck("changed-test-files", ["python3", "-m", "pytest", *test_files, "-q"], "new or changed tests must pass", timeout=240)]
    return []


def default_evidence_for_layer(layer: str) -> list[EvidenceRule]:
    base = [
        EvidenceRule("changed-files", "evidence must name changed files or commits", keywords_any=(".py", ".md", ".json", "commit", "diff", "changed")),
        EvidenceRule("tests-run", "evidence must record tests or executable checks", keywords_any=("pytest", "test", "check", "verified", "passed")),
        EvidenceRule("no-bypass", "evidence must not describe bypassing gates", patterns=(r"\b(no --no-verify|without --no-verify|normal commit|gate passed)\b",), required=False),
    ]
    layer_extra = {
        "security": [EvidenceRule("security-proof", "security work must include scan/threat/risk evidence", keywords_any=("gitleaks", "secret", "threat", "risk", "auth", "permission"))],
        "memory": [EvidenceRule("durability-proof", "memory work must prove durable persistence or readback", keywords_any=("readback", "durable", "persist", "postgres", "git archive", "chroma"))],
        "documentation": [EvidenceRule("doc-preservation", "documentation work must state preservation/migration outcome", keywords_any=("preserved", "migrated", "template", "frontmatter", "human-readable"))],
        "infrastructure": [EvidenceRule("system-proof", "infrastructure work must include system or repo-state proof", keywords_any=("lock", "atomic", "systemctl", "health", "registry", "transaction"))],
        "orchestration": [EvidenceRule("routing-proof", "orchestration work must prove routing/ordering behavior", keywords_any=("route", "dispatch", "advisor", "context", "order"))],
    }
    return base + layer_extra.get(layer, [])
