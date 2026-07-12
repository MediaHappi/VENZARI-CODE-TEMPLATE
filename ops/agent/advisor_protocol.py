#!/usr/bin/env python3
"""Provider-neutral advisor protocol for YOUR-PROJECT."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AdvisorRequest:
    request_id: str
    task_id: str
    title: str
    layer: str
    advisor_type: str
    requester: str
    prompt_template: str
    task: dict[str, Any] = field(default_factory=dict)
    context_files: list[str] = field(default_factory=list)
    required_outputs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    concurrency_policy: str = "one_active_implementation_agent_plus_optional_single_advisor"

    @classmethod
    def from_task(cls, task: dict, *, requester: str = "claude-code", advisor_type: str = "task_review", prompt_template: str = "task_review") -> "AdvisorRequest":
        task_id = task.get("id") or task.get("task_id") or "unknown"
        return cls(
            request_id=f"ADVREQ-{task_id}-{int(datetime.now(timezone.utc).timestamp())}",
            task_id=task_id,
            title=task.get("title", ""),
            layer=task.get("layer", "uncategorized"),
            advisor_type=advisor_type,
            requester=requester,
            prompt_template=prompt_template,
            task=task,
            required_outputs=["verdict", "risks", "required_fixes", "verification_plan", "confidence"],
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AdvisorVerdict:
    request_id: str
    advisor_type: str
    provider: str
    approved: bool
    verdict: str
    risks: list[str]
    required_fixes: list[str]
    verification_plan: list[str]
    confidence: int
    raw_output: str = ""
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def deterministic(cls, request: AdvisorRequest, *, risks: list[str], fixes: list[str], verification: list[str], approved: bool) -> "AdvisorVerdict":
        return cls(
            request_id=request.request_id,
            advisor_type=request.advisor_type,
            provider="deterministic",
            approved=approved,
            verdict="APPROVED" if approved else "NEEDS_REVISION",
            risks=risks,
            required_fixes=fixes,
            verification_plan=verification,
            confidence=70 if approved else 55,
            raw_output=json.dumps({"method": "deterministic advisor fallback"}),
        )


def write_trace(repo: Path, request: AdvisorRequest, verdict: AdvisorVerdict) -> Path:
    trace_dir = repo / ".advisors" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{request.request_id}.json"
    path.write_text(json.dumps({"request": request.to_dict(), "verdict": verdict.to_dict()}, indent=2))
    return path
