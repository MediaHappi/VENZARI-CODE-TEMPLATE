"""
ops/agent/skill_matcher.py

Intelligent skill recommendation for task_manager.py.
Uses weighted keyword scoring against a structured skill index.

Usage:
    from skill_matcher import recommend_skills
    skills = recommend_skills("Build Slack bot with Bolt SDK Socket Mode", top_n=3)

    # CLI:
    python3 skill_matcher.py "Build Slack bot" --top 3
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

_REPO = Path(__file__).parent.parent.parent
_INDEX_PATH = _REPO / "ops" / "agent" / "skill_index.json"


# ---------------------------------------------------------------------------
# Skill index — structured knowledge base for scoring
# Each entry: name, triggers (high-weight), keywords (lower-weight), role
# ---------------------------------------------------------------------------
_BUILTIN_INDEX = [
    # === YOUR-AI Native Skills ===
    {"name": "claim-task",              "triggers": ["session", "startup", "start", "claim", "begin"], "keywords": ["task", "mandatory"], "role": "*"},
    {"name": "memory-write",            "triggers": ["memory", "recall", "store", "persist", "observation"], "keywords": ["l3", "claude-mem", "learning"], "role": "memory"},
    {"name": "worktree-task",           "triggers": ["infra", "infrastructure", "change", "files", "worktree", "git"], "keywords": ["isolated", "risky", "large"], "role": "infrastructure"},
    {"name": "escalate",                "triggers": ["escalate", "stuck", "three", "strike", "blocked", "failed 3"], "keywords": ["billy", "inbox", "halt"], "role": "*"},
    {"name": "infra",                   "triggers": ["docker", "systemd", "nginx", "vps", "container", "service", "deploy"], "keywords": ["ssh", "config", "restart", "compose"], "role": "infrastructure"},
    {"name": "build-and-verify",        "triggers": ["build", "deploy", "ship", "curl", "verify", "http 200"], "keywords": ["check", "test", "after"], "role": "*"},
    {"name": "deploy-script",           "triggers": ["script", "cron", "bin", "deploy", "/usr/local/bin"], "keywords": ["install", "executable", "chmod"], "role": "devops"},
    {"name": "debug-telegram",          "triggers": ["telegram", "openclaw", "message", "bot", "chat"], "keywords": ["webhook", "polling", "response"], "role": "backend"},
    {"name": "telegram-ops",            "triggers": ["telegram", "openclaw", "claw"], "keywords": ["session", "model", "restart"], "role": "backend"},
    {"name": "observability",           "triggers": ["log", "monitor", "health", "grafana", "loki", "alert"], "keywords": ["check", "status", "metric"], "role": "devops"},
    {"name": "security-review",         "triggers": ["security", "secret", "token", "key", "permission", "audit", "scan"], "keywords": ["exposed", "firewall", "ufw", "port"], "role": "security"},
    {"name": "architecture-review",     "triggers": ["architecture", "design", "plan", "adr", "decision", "tradeoff"], "keywords": ["review", "system", "structure"], "role": "backend"},
    {"name": "ai-model-ops",            "triggers": ["model", "ollama", "inference", "router", "venzarai", "groq", "mistral"], "keywords": ["llm", "embedding", "token", "fallback"], "role": "backend"},
    {"name": "dashboard-ops",           "triggers": ["dashboard", "flask", "web", "ui", "readykit", "celery"], "keywords": ["template", "route", "frontend", "5002"], "role": "frontend"},
    {"name": "business-automation",     "triggers": ["n8n", "hubspot", "crm", "workflow", "automation", "marketing"], "keywords": ["acelle", "email", "social"], "role": "backend"},
    {"name": "content-pipeline",        "triggers": ["content", "generate", "post", "social", "blog", "article"], "keywords": ["ai-content-engine", "worker"], "role": "backend"},

    # === Agent-Skills Vendor ===
    {"name": "agent-skills/debugging-and-error-recovery", "triggers": ["debug", "error", "crash", "fail", "broken", "fix", "issue"], "keywords": ["traceback", "exception", "log", "diagnose"], "role": "*"},
    {"name": "agent-skills/incremental-implementation",   "triggers": ["implement", "build", "create", "feature", "add"], "keywords": ["step", "incremental", "phase"], "role": "backend"},
    {"name": "agent-skills/test-driven-development",      "triggers": ["test", "tdd", "verify", "check", "validate", "unit"], "keywords": ["assert", "coverage", "spec"], "role": "testing"},
    {"name": "agent-skills/planning-and-task-breakdown",  "triggers": ["plan", "spec", "design", "breakdown", "phase", "scope"], "keywords": ["task", "dod", "criteria"], "role": "*"},
    {"name": "agent-skills/spec-driven-development",      "triggers": ["spec", "requirement", "prd", "feature", "define"], "keywords": ["acceptance", "criteria", "user story"], "role": "backend"},
    {"name": "agent-skills/code-review-and-quality",      "triggers": ["review", "quality", "pr", "code", "check"], "keywords": ["lint", "style", "clean"], "role": "backend"},
    {"name": "agent-skills/code-simplification",          "triggers": ["refactor", "simplify", "clean", "optimize", "cleanup"], "keywords": ["reduce", "abstract", "reuse"], "role": "backend"},
    {"name": "agent-skills/security-and-hardening",       "triggers": ["security", "harden", "secret", "scan", "permission", "firewall", "port", "binding"], "keywords": ["ufw", "ssl", "auth", "exposure"], "role": "security"},
    {"name": "agent-skills/shipping-and-launch",          "triggers": ["ship", "deploy", "release", "launch", "production", "live"], "keywords": ["rollout", "verify", "smoke"], "role": "devops"},
    {"name": "agent-skills/deprecation-and-migration",    "triggers": ["migrate", "deprecate", "replace", "remove", "upgrade", "transition"], "keywords": ["backward", "legacy", "stale"], "role": "backend"},
    {"name": "agent-skills/documentation-and-adrs",       "triggers": ["doc", "runbook", "adr", "decision", "readme", "write", "update docs"], "keywords": ["architecture", "record", "markdown"], "role": "backend"},
    {"name": "agent-skills/performance-optimization",     "triggers": ["performance", "slow", "latency", "speed", "optimize", "benchmark"], "keywords": ["profile", "cache", "timeout"], "role": "backend"},
    {"name": "agent-skills/api-and-interface-design",     "triggers": ["api", "endpoint", "rest", "interface", "contract", "openapi"], "keywords": ["schema", "route", "http", "json"], "role": "backend"},
    {"name": "agent-skills/frontend-ui-engineering",      "triggers": ["ui", "frontend", "html", "css", "javascript", "template", "component"], "keywords": ["dark theme", "responsive", "jinja", "js"], "role": "frontend"},
    {"name": "agent-skills/browser-testing-with-devtools","triggers": ["browser", "test", "e2e", "chrome", "devtools", "selenium"], "keywords": ["visual", "render", "playwright"], "role": "testing"},
    {"name": "agent-skills/doubt-driven-development",     "triggers": ["doubt", "risk", "uncertainty", "stress-test", "question", "validate design"], "keywords": ["assumption", "edge case", "tradeoff"], "role": "*"},
    {"name": "agent-skills/interview-me",                 "triggers": ["unclear", "vague", "requirement", "interview", "clarify", "ambiguous"], "keywords": ["question", "scope"], "role": "*"},
    {"name": "agent-skills/source-driven-development",    "triggers": ["docs", "official", "reference", "spec", "standard", "rfc"], "keywords": ["documentation", "canonical", "source"], "role": "backend"},

    # === Mattpocock Skills ===
    {"name": "mattpocock/engineering/diagnose",  "triggers": ["diagnose", "triage", "understand", "investigate", "explore", "audit"], "keywords": ["codebase", "map", "root cause"], "role": "*"},
    {"name": "mattpocock/engineering/to-prd",    "triggers": ["prd", "product", "spec", "document", "feature", "plan"], "keywords": ["requirement", "user story", "criteria"], "role": "backend"},
    {"name": "mattpocock/engineering/to-issues", "triggers": ["issue", "github", "ticket", "task", "story", "bug"], "keywords": ["create", "track", "backlog"], "role": "devops"},
    {"name": "mattpocock/engineering/triage",    "triggers": ["triage", "prioritize", "assess", "scope", "survey"], "keywords": ["codebase", "health", "debt"], "role": "*"},
    {"name": "mattpocock/productivity/handoff",  "triggers": ["handoff", "summary", "context", "brief", "session"], "keywords": ["next", "state", "transfer"], "role": "*"},
    {"name": "mattpocock/productivity/write-a-skill", "triggers": ["skill", "create skill", "write skill", "new skill"], "keywords": ["catalog", "template", "SKILL.md"], "role": "*"},

    # === Alirezarezvani Vendor ===
    {"name": "alirezarezvani/container-health-matrix", "triggers": ["container", "docker", "health", "matrix", "status all"], "keywords": ["ps", "inspect", "all services"], "role": "devops"},
    {"name": "alirezarezvani/cron-audit",               "triggers": ["cron", "crontab", "scheduled", "job", "timer"], "keywords": ["audit", "duplicate", "stale"], "role": "devops"},
    {"name": "alirezarezvani/git-branch-cleanup",       "triggers": ["worktree", "branch", "cleanup", "stale", "prune"], "keywords": ["git", "merged", "old"], "role": "devops"},
    {"name": "alirezarezvani/incident-timeline",        "triggers": ["incident", "outage", "post-mortem", "timeline", "root cause"], "keywords": ["event", "sequence", "failure"], "role": "*"},
    {"name": "alirezarezvani/ssh-tunnel-test",          "triggers": ["ssh", "tunnel", "connectivity", "port", "forward"], "keywords": ["test", "diagnose", "verify"], "role": "infrastructure"},

    # === Operators ===
    {"name": "operators/deploy-feature",   "triggers": ["deploy", "feature", "ship", "complete", "end-to-end"], "keywords": ["infra", "verify", "memory"], "role": "devops"},
    {"name": "operators/audit-and-fix",    "triggers": ["audit", "fix", "pre-release", "sweep", "verify all"], "keywords": ["check", "scan", "confirm"], "role": "*"},
    {"name": "operators/claim-and-execute","triggers": ["claim", "execute", "session", "start work", "autonomous"], "keywords": ["task", "complete", "run"], "role": "*"},

    # === Interface / Slack / Discord / Voice ===
    {"name": "build-and-verify",           "triggers": ["slack", "discord", "bolt", "socket mode", "interface", "api"], "keywords": ["bot", "webhook", "token"], "role": "backend"},
    {"name": "agent-skills/api-and-interface-design", "triggers": ["slack api", "discord api", "voice", "tts", "piper"], "keywords": ["integration", "channel", "event"], "role": "backend"},
]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _score_skill(skill: dict, tokens: set[str], text_lower: str) -> float:
    score = 0.0
    for trigger in skill.get("triggers", []):
        if trigger in text_lower:
            score += 3.0  # high-weight: exact phrase match
        elif all(t in tokens for t in _tokenize(trigger)):
            score += 2.0  # medium: all words present
    for kw in skill.get("keywords", []):
        if kw in text_lower:
            score += 1.0
        elif any(t in tokens for t in _tokenize(kw)):
            score += 0.3
    return score


def recommend_skills(task_text: str, role: str = None, top_n: int = 3) -> list[str]:
    """
    Return top_n skill names most relevant to task_text.

    Args:
        task_text: Combined task title + description + layer
        role:      Optional agent role to filter/boost role-matched skills
        top_n:     Number of results to return

    Returns:
        List of skill name strings (most relevant first).
    """
    if not task_text:
        return ["claim-task", "build-and-verify"]

    text_lower = task_text.lower()
    tokens = set(_tokenize(text_lower))

    scored = []
    for skill in _BUILTIN_INDEX:
        score = _score_skill(skill, tokens, text_lower)
        if score <= 0:
            continue
        # Boost role-matched skills
        if role and (skill.get("role") == role or skill.get("role") == "*"):
            score *= 1.3
        scored.append((score, skill["name"]))

    scored.sort(reverse=True)

    # Deduplicate and take top_n
    seen = set()
    result = []
    for score, name in scored:
        if name not in seen:
            seen.add(name)
            result.append(name)
        if len(result) >= top_n:
            break

    # Always include claim-task if not already there and result is short
    if "claim-task" not in result and len(result) < top_n:
        result.append("claim-task")

    return result or ["claim-task", "build-and-verify"]


def create_skill_matching_finding(task_text: str, recommended_skills: list):
    """REAL: Export skill matching decision → findings"""
    try:
        if not recommended_skills:
            return
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-skill-match-{hash(task_text) % 1000000}-{int(datetime.now().timestamp())}",
            service="skill-matcher",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Skills matched for task: {task_text[:60]}",
            evidence=[{"type": "skill_match", "text": f"Task: {task_text}, Recommended: {', '.join(recommended_skills)}"}],
            related_metrics={"skill_count": len(recommended_skills), "recommended_skills": recommended_skills}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def load_index() -> list[dict]:
    """Load skill index from JSON file if available, else use builtin."""
    if _INDEX_PATH.exists():
        try:
            return json.loads(_INDEX_PATH.read_text())
        except Exception:
            pass
    return _BUILTIN_INDEX


def save_index():
    """Persist builtin index to JSON for external tooling."""
    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_PATH.write_text(json.dumps(_BUILTIN_INDEX, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Recommend skills for a task")
    parser.add_argument("text", help="Task title/description")
    parser.add_argument("--top", type=int, default=3, help="Number of results")
    parser.add_argument("--role", default=None, help="Agent role for boosting")
    parser.add_argument("--save-index", action="store_true", help="Save index to JSON")
    args = parser.parse_args()

    if args.save_index:
        save_index()
        print(f"Index saved to {_INDEX_PATH}")
        sys.exit(0)

    results = recommend_skills(args.text, role=args.role, top_n=args.top)

    # Export skill matching decision as finding
    create_skill_matching_finding(args.text, results)

    for i, skill in enumerate(results, 1):
        print(f"  {i}. {skill}")
