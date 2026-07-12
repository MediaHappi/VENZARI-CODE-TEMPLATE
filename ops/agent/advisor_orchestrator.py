#!/usr/bin/env python3
"""Advisor framework v2 orchestration entrypoint."""

from __future__ import annotations

import json
import os
from pathlib import Path

from advisor_provider_adapters import get_adapter
from advisor_prompt_templates import select_template
from advisor_protocol import AdvisorRequest, write_trace


def repo_dir() -> Path:
    """PROJECT_CTO_PATH wins if set (tests use this for isolation). Otherwise resolve
    relative to this script's own location, not a hardcoded '/opt/YOUR-PROJECT' -- the
    same class of bug found and fixed in ops/agent/state_archiver.py during task
    O0000000006 (a hardcoded fallback made a worktree copy of the script silently
    operate on the main repo's files instead of its own)."""
    env_path = os.environ.get("PROJECT_CTO_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2]


def review_task(task: dict, *, requester: str = "claude-code", advisor_type: str | None = None,
                 backend: str | None = None, stakes: str = "low") -> dict:
    """stakes="low" (default) always uses the fast deterministic adapter -- a real
    CLI-backed review (claude-code/codex/aider) only fires when stakes="high" (a
    genuinely complex/ambiguous case) or the caller explicitly names a backend. See
    get_adapter()'s docstring for why this default changed (task O0000000011)."""
    template = select_template(task, advisor_type)
    request = AdvisorRequest.from_task(task, requester=requester, advisor_type=template, prompt_template=template)
    request.context_files = context_files_for_task(task)
    adapter = get_adapter(backend, stakes=stakes)
    verdict = adapter.invoke(request)
    trace_path = write_trace(repo_dir(), request, verdict)
    data = verdict.to_dict()
    data["trace_path"] = str(trace_path)
    return data


def context_files_for_task(task: dict) -> list[str]:
    layer = (task.get("layer") or "").lower()
    files = ["CLAUDE.md", "GOLDEN_RULES.md", "system-map/CURRENT_STATE.md"]
    if layer:
        files.append(f"agents/roles/{layer}.md")
    text = f"{task.get('title','')} {task.get('description','')}".lower()
    if "runbook" in text:
        files.append("docs/runbooks/TEMPLATE.md")
    if "gate" in text:
        files.append("docs/governance/CLOSING-GATE-SYSTEM.md")
    if "advisor" in text:
        files.append("docs/governance/ADVISOR-SYSTEM.md")
    return files


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task_json", help="Task JSON file to review")
    parser.add_argument("--requester", default=os.environ.get("ADVISOR_REQUESTER", "claude-code"))
    parser.add_argument("--backend", default=os.environ.get("ADVISOR_AGENT_BACKEND"))
    args = parser.parse_args()
    task = json.loads(Path(args.task_json).read_text())
    print(json.dumps(review_task(task, requester=args.requester, backend=args.backend), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
