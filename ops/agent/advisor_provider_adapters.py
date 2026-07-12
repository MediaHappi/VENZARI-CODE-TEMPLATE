#!/usr/bin/env python3
"""Advisor provider adapters for Claude Code, Codex, Aider, and local fallback."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from advisor_protocol import AdvisorRequest, AdvisorVerdict
from advisor_prompt_templates import render_prompt


class AdvisorAdapter:
    name = "base"

    def available(self) -> bool:
        return False

    def invoke(self, request: AdvisorRequest, timeout: int = 600) -> AdvisorVerdict:
        raise NotImplementedError


class DeterministicAdvisorAdapter(AdvisorAdapter):
    name = "deterministic"

    def available(self) -> bool:
        return True

    def invoke(self, request: AdvisorRequest, timeout: int = 60) -> AdvisorVerdict:
        task = request.task
        risks: list[str] = []
        fixes: list[str] = []
        verification: list[str] = []
        desc = task.get("description", "") or ""
        dod = task.get("dod") or task.get("acceptance_criteria") or []
        if len(desc) < 120:
            risks.append("Task description is too short for autonomous execution.")
            fixes.append("Expand description with approach, files, tests, and rollback.")
        if not dod:
            risks.append("Task has no Definition of Done.")
            fixes.append("Add concrete DoD items before execution.")
        if "test" not in (desc + " ".join(map(str, dod))).lower():
            verification.append("Add or identify task-specific tests.")
        verification.append("Run typed closing gate and include evidence.")
        return AdvisorVerdict.deterministic(request, risks=risks, fixes=fixes, verification=verification, approved=not fixes)


class CommandAdvisorAdapter(AdvisorAdapter):
    command: list[str] = []

    def available(self) -> bool:
        return bool(self.command) and subprocess.run(["bash", "-lc", f"command -v {self.command[0]}"], capture_output=True).returncode == 0

    def invoke(self, request: AdvisorRequest, timeout: int = 600) -> AdvisorVerdict:
        prompt = render_prompt(request)
        proc = subprocess.run(self.command, input=prompt, text=True, capture_output=True, timeout=timeout)
        raw = (proc.stdout or "") + ("\nSTDERR:\n" + proc.stderr if proc.stderr else "")
        approved = proc.returncode == 0 and "NEEDS_REVISION" not in raw.upper()
        risks = [] if approved else [f"{self.name} returned non-approval or non-zero exit {proc.returncode}"]
        return AdvisorVerdict(
            request_id=request.request_id,
            advisor_type=request.advisor_type,
            provider=self.name,
            approved=approved,
            verdict="APPROVED" if approved else "NEEDS_REVISION",
            risks=risks,
            required_fixes=[] if approved else ["Review raw advisor output and apply required fixes."],
            verification_plan=["Run task-specific tests", "Run typed closing gate"],
            confidence=80 if approved else 50,
            raw_output=raw[-8000:],
        )


class ClaudeCodeAdvisorAdapter(CommandAdvisorAdapter):
    name = "claude-code"
    command = ["claude", "--print"]


class CodexAdvisorAdapter(CommandAdvisorAdapter):
    name = "codex"
    command = ["codex", "exec", "-"]


class AiderAdvisorAdapter(CommandAdvisorAdapter):
    name = "aider"
    command = ["aider", "--message", "-"]


def get_adapter(name: str | None = None, *, stakes: str = "low") -> AdvisorAdapter:
    """'auto' used to mean "prefer a real CLI-backed adapter whenever one happens to be
    installed" -- on a machine where `claude` is on PATH (true for essentially every dev
    box running this code), that made EVERY advisor call, including routine/low-stakes
    ones, silently invoke a real, multi-minute nested `claude --print` call. Billy: "we
    save advisor for the big things like it is designed... we need a better auto system
    to make decisions by itself on lower tier things." Found live during task O0000000007's
    own completion: 3+ real advisor calls fired across routine retries.

    Fix: 'auto' now only prefers a real CLI-backed adapter when the caller explicitly
    marks the request as high-stakes (stakes="high"). Low-stakes (the default) always
    uses the fast deterministic adapter, regardless of what's installed. An explicit
    backend name (e.g. --backend claude-code) still always wins, for genuine opt-in."""
    requested = (name or os.environ.get("ADVISOR_AGENT_BACKEND") or "auto").lower()
    adapters = {
        "claude": ClaudeCodeAdvisorAdapter(),
        "claude-code": ClaudeCodeAdvisorAdapter(),
        "codex": CodexAdvisorAdapter(),
        "aider": AiderAdvisorAdapter(),
        "deterministic": DeterministicAdvisorAdapter(),
    }
    if requested != "auto":
        return adapters.get(requested, DeterministicAdvisorAdapter())
    if stakes != "high":
        return DeterministicAdvisorAdapter()
    for candidate in (ClaudeCodeAdvisorAdapter(), CodexAdvisorAdapter(), AiderAdvisorAdapter()):
        if candidate.available():
            return candidate
    return DeterministicAdvisorAdapter()
