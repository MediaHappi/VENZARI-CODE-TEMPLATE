#!/usr/bin/env python3
"""Advisor prompt templates for task-specific review."""

from __future__ import annotations

import json


TEMPLATES = {
    "task_review": {
        "purpose": "Review one task for completeness, risk, dependencies, and execution clarity.",
        "required": ["verdict", "risks", "required_fixes", "verification_plan", "confidence"],
    },
    "historical_verification": {
        "purpose": "Audit completed task evidence and identify tasks that need reopening.",
        "required": ["sampled_tasks", "invalid_completions", "reopen_tasks", "confidence"],
    },
    "repo_map": {
        "purpose": "Review repo-map/context-routing architecture before implementation.",
        "required": ["map_strategy", "context_budget", "routing_rules", "risks"],
    },
    "closing_gate": {
        "purpose": "Review typed closing gate behavior for bypasses, deadlocks, and missing proof.",
        "required": ["bypass_risks", "deadlock_risks", "required_tests", "verdict"],
    },
    "documentation": {
        "purpose": "Review living docs for structure, preservation, human readability, and context bloat.",
        "required": ["preservation_risks", "context_risks", "template_fixes", "verification_plan"],
    },
    "security": {
        "purpose": "Review security-sensitive work for secrets, permissions, auth, and blast radius.",
        "required": ["threats", "secret_scan", "permission_risks", "required_fixes"],
    },
}


def select_template(task: dict, advisor_type: str | None = None) -> str:
    text = f"{task.get('title','')} {task.get('description','')} {task.get('layer','')}".lower()
    if advisor_type in TEMPLATES:
        return advisor_type
    if "historical" in text or "re-verification" in text:
        return "historical_verification"
    if "repo map" in text or "context router" in text or "codegraph" in text:
        return "repo_map"
    if "gate" in text or "closing" in text:
        return "closing_gate"
    if "doc" in text or "wiki" in text or "runbook" in text:
        return "documentation"
    if "security" in text or "secret" in text or "permission" in text:
        return "security"
    return "task_review"


def render_prompt(request) -> str:
    template = TEMPLATES.get(request.prompt_template, TEMPLATES["task_review"])
    task_json = json.dumps(request.task, indent=2, sort_keys=True)
    required = "\n".join(f"- {item}" for item in template["required"])
    context = "\n".join(f"- {path}" for path in request.context_files) or "- none"
    return f"""You are a YOUR-PROJECT advisor.

Purpose:
{template['purpose']}

Requester:
{request.requester}

Task:
{task_json}

Context files:
{context}

Required output fields:
{required}

Return concise JSON with these fields:
- verdict: APPROVED or NEEDS_REVISION
- risks: list of concrete risks
- required_fixes: list of fixes required before completion
- verification_plan: list of commands/checks the executor must run
- confidence: integer 0-100

Do not invent evidence. If evidence is missing, say exactly what must be gathered.
Do not suggest swarms, parallel implementation agents, or multiple concurrent coding agents. [YOUR-AI-NAME] allows one active implementation agent plus, when needed, one advisor helper.
"""
