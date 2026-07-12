#!/usr/bin/env python3
"""
Skill router — fast capability-tag index for task creation + findings export.

Indexes all 213 skills by capability tags so task_manager.py create
can auto-suggest top 3 relevant skills without reading SKILL_CATALOG.md.

ENHANCED: Now creates findings for routing decisions → wiki ingestion

Usage:
  python3 skill_router.py suggest "deploy docker container"  # top 3 skills
  python3 skill_router.py index                              # rebuild index
  python3 skill_router.py search infra                       # skills tagged 'infra'
"""
import sys, json, os
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# REAL systems for findings export
sys.path.insert(0, '/opt/YOUR-PROJECT/ops/agent')
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

REPO_ROOT = Path(os.environ.get("PROJECT_CTO_PATH", "/opt/YOUR-PROJECT"))
INDEX_PATH = REPO_ROOT / "ops/agent/skill_router_index.json"

# Tag definitions: keyword → [skill-keys to suggest]
TAG_MAP = {
    "infra":        ["infra", "worktree-task", "build-and-verify"],
    "docker":       ["infra", "build-and-verify", "observability"],
    "deploy":       ["agent-skills/shipping-and-launch", "worktree-task", "build-and-verify"],
    "telegram":     ["telegram-ops", "debug-telegram", "observability"],
    "venzarai-router":      ["venzarai-router-config", "ai-model-ops", "build-and-verify"],
    "ollama":       ["ai-model-ops", "venzarai-router-config", "ai-trainer"],
    "model":        ["ai-model-ops", "venzarai-router-config", "ai-trainer"],
    "memory":       ["memory-write", "observability", "agent-skills/debugging-and-error-recovery"],
    "redis":        ["memory-write", "observability"],
    "postgres":     ["memory-write", "observability"],
    "chromadb":     ["memory-write", "observability"],
    "embed":        ["memory-write", "ai-model-ops"],
    "security":     ["security-review", "agent-skills/security-and-hardening", "trailofbits/audit-context-building"],
    "secret":       ["security-review", "agent-skills/security-and-hardening"],
    "audit":        ["security-review", "trailofbits/audit-context-building"],
    "pentest":      ["zebbern/ethical-hacking-methodology", "zebbern/pentest-checklist", "security-review"],
    "n8n":          ["n8n-skills/n8n-workflow-patterns", "n8n-skills/n8n-mcp-tools-expert", "business-automation"],
    "workflow":     ["n8n-skills/n8n-workflow-patterns", "business-automation"],
    "dashboard":    ["dashboard-ops", "build-and-verify"],
    "flask":        ["dashboard-ops", "build-and-verify"],
    "celery":       ["dashboard-ops", "build-and-verify"],
    "build":        ["github-search", "build-and-verify", "worktree-task"],
    "create":       ["github-search", "build-and-verify"],
    "implement":    ["github-search", "agent-skills/test-driven-development"],
    "test":         ["reviewer", "build-and-verify", "agent-skills/test-driven-development"],
    "verify":       ["reviewer", "build-and-verify"],
    "refactor":     ["agent-skills/code-simplification", "reviewer"],
    "debug":        ["agent-skills/debugging-and-error-recovery", "observability"],
    "error":        ["agent-skills/debugging-and-error-recovery", "observability"],
    "ssh":          ["infra", "worktree-task"],
    "tunnel":       ["infra", "venzarai-router-config"],
    "backup":       ["infra", "build-and-verify"],
    "cron":         ["infra", "build-and-verify"],
    "nginx":        ["infra", "build-and-verify"],
    "role":         ["agent-skills/planning-and-task-breakdown", "reviewer"],
    "skill":        ["agent-skills/planning-and-task-breakdown", "reviewer"],
    "github":       ["github-search", "agent-skills/git-workflow-and-versioning"],
    "swarm":        ["ruflo/swarm-advanced", "ruflo/swarm-orchestration"],
    "orchestrat":   ["ruflo/hive-mind-advanced", "ruflo/flow-nexus-swarm"],
    "sparc":        ["ruflo/sparc-methodology"],
    "agentdb":      ["ruflo/agentdb-memory-patterns", "memory-write"],
    "contract":     ["trailofbits/building-secure-contracts/skills/audit-prep-assistant"],
    "mutation":     ["trailofbits/mutation-testing/skills/mutation-testing"],
    "gh-cli":       ["trailofbits/.codex/skills/gh-cli"],
    "training":     ["ai-model-ops", "agent-skills/test-driven-development"],
    "ollama model": ["ai-trainer", "ai-model-ops"],
    "fine-tun":     ["ai-trainer", "ai-model-ops"],
    "document":     ["agent-skills/documentation-and-adrs", "reviewer"],
    "update":       ["agent-skills/documentation-and-adrs", "worktree-task"],
}

def suggest(query: str, top_n: int = 3, export_finding: bool = True) -> list[str]:
    """Return top N skill keys relevant to the query. Export finding if export_finding=True."""
    q = query.lower()
    scores: dict[str, int] = {}
    for tag, skills in TAG_MAP.items():
        if tag in q:
            for i, skill in enumerate(skills):
                scores[skill] = scores.get(skill, 0) + (len(skills) - i)
    ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
    # Always include github-search for BUILD tasks (Rule 16)
    if any(w in q for w in ("build", "create", "implement", "add ", "write", "scaffold")):
        if "github-search" not in ranked[:top_n]:
            ranked = ["github-search"] + [r for r in ranked if r != "github-search"]
    result = ranked[:top_n] if ranked else ["claim-task", "worktree-task", "build-and-verify"]

    # Create finding for routing decision
    if export_finding:
        create_routing_finding(query, result)

    return result

def search_by_tag(tag: str) -> list[str]:
    """Return all skills associated with a tag."""
    return TAG_MAP.get(tag.lower(), [])

def build_index():
    """Build and save the full tag→skill index to JSON."""
    INDEX_PATH.write_text(json.dumps(TAG_MAP, indent=2))
    print(f"Index saved to {INDEX_PATH} ({len(TAG_MAP)} tags)")

def create_routing_finding(query: str, skills: List[str]):
    """REAL: Create finding for skill routing decision → wiki"""
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-routing-{hash(query) % 1000000}-{int(datetime.now().timestamp())}",
            service="skill-router",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Skill routing: '{query}' → {', '.join(skills[:3])}",
            evidence=[{"type": "routing", "text": f"Query: {query}, Suggested: {skills}"}],
            related_metrics={"skill_count": len(skills), "query_length": len(query)}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
        return True
    except Exception as e:
        print(f"  [finding export failed: {e}]", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "suggest" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        skills = suggest(query)
        print(f"Top skills for: {query!r}")
        for s in skills:
            print(f"  python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load {s}")
    elif cmd == "search" and len(sys.argv) > 2:
        tag = sys.argv[2]
        skills = search_by_tag(tag)
        print(f"Skills tagged '{tag}': {skills}")
    elif cmd == "index":
        build_index()
    else:
        print(__doc__)
