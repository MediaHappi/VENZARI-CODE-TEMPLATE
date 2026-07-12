#!/usr/bin/env python3
"""
6-layer context injection for [YOUR-AI-NAME] agents — with Layer 0 skill hints + Layer 6 GitHub patterns.

Queries all relevant memory layers at task claim time and returns a
bounded context block (<500 tokens). Layers that are unavailable are
skipped — they never block task start.

Usage:
  python3 inject_context.py "<task description or query>"
  python3 inject_context.py "<query>" --layers l0,l4,l3,l5,l6
  python3 inject_context.py "<query>" --json
  python3 inject_context.py "<query>" --task-type build --scope voice

Layers:
  L0: skills      — skill catalog hints (fast, local, no network)
  L4: codegraph   — structural code context (calls, definitions, impact)
  L3: claude-mem  — semantic engineering observations and history
  L5: git         — recent ADRs from docs/architecture/decision-log.md
  L6: patterns    — repo-intelligence/patterns/ + reference-repos/ matches (task 1006)
  L2: postgres    — (optional, use --layers l2 for system config queries)
  L1: redis       — (optional, use --layers l1 for runtime state queries)

Architecture: docs/architecture/MEMORY_ARCHITECTURE.md
Governance:   docs/architecture/MEMORY-GOVERNANCE.md
"""

import os
import sys
import json
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

PROJECT_CTO = "/opt/YOUR-PROJECT"
OPS = f"{PROJECT_CTO}/ops/agent"

# Task 1648: Import specialist router for 8-specialist persona selection
try:
    from specialist_router import detect_specialist, format_specialist_prompt
    HAS_SPECIALIST_ROUTER = True
except ImportError:
    HAS_SPECIALIST_ROUTER = False

# Task 1657: Import peer reasoning for L3b peer-centric context
# Task 1658: Import format_peer_context for enhanced context formatting
try:
    from peer_reasoning import PeerReasoning, format_peer_context
    HAS_PEER_REASONING = True
except ImportError:
    HAS_PEER_REASONING = False
    format_peer_context = lambda x, **kw: ""  # Graceful fallback

# Task 1663: Import memory recall for session-based autonomous learning (Phase 5C-4)
try:
    from memory_recall import MemoryRecall, format_memory_context
    HAS_MEMORY_RECALL = True
except ImportError:
    HAS_MEMORY_RECALL = False
    format_memory_context = lambda x, **kw: ""  # Graceful fallback

# Token budget enforcement (Task 1310)
BUDGET_TOKENS = {
    'L1': 200,   # Redis runtime state
    'L2': 300,   # PostgreSQL config
    'L3': 1000,  # Claude-mem semantic
    'L4': 300,   # Codegraph structural
    'L5': 200,   # ADR decision log
    'L6': 100,   # GitHub patterns
}
BUDGET_TOTAL = 2000

# Legacy char-based limits (deprecated but kept for backwards compat)
MAX_CHARS_PER_LAYER = 500
MAX_TOTAL_CHARS = 2000
MAX_ADR_LOG_LINES = 10

# Task type budgets (Task 1310 - different allocations per task type)
TASK_BUDGETS = {
    'code': {'L3': 600, 'L4': 500},  # code tasks need more codegraph
    'arch': {'L5': 300, 'L3': 700},  # arch tasks need more history
    'infra': {'L2': 400, 'L3': 600}, # infra needs config + memory
}

# Keywords → skills for Layer 0 hints (expanded with vendor patterns from SKILL_SCANNER_REPORT_2)
_SKILL_HINTS = [
    (["telegram", "openclaw", "bot", "message"], ["telegram-ops", "debug-telegram"]),
    (["infra", "docker", "container", "systemd", "nginx", "ssh", "tunnel", "cron"], ["infra", "worktree-task", "build-and-verify"]),
    (["venzarai-router", "model", "ollama", "routing", "fallback", "429"], ["venzarai-router-config", "ai-model-ops"]),
    (["memory", "l3", "claude-mem", "chroma", "redis", "recall"], ["memory-write", "observability"]),
    (["security", "secret", "key", "permission", "audit", "scan"], ["security-review", "agent-skills/security-and-hardening"]),
    (["dashboard", "flask", "celery", "worker", "route"], ["dashboard-ops", "build-and-verify"]),
    (["business", "n8n", "hubspot", "crm", "workflow", "automation"], ["business-automation"]),
    (["content", "social", "post", "generate"], ["content-pipeline"]),
    (["debug", "error", "crash", "fail", "broken"], ["agent-skills/debugging-and-error-recovery", "observability"]),
    (["architecture", "adr", "decision", "design"], ["architecture-review", "agent-skills/documentation-and-adrs", "agent-skills/planning-and-task-breakdown"]),
    (["review", "coherence", "plan", "complex", "specification", "sparc"], ["architecture-review", "ruflo-skills/sparc-methodology", "agent-skills/planning-and-task-breakdown"]),
    (["tdd", "test", "verify", "validate", "quality"], ["reviewer", "build-and-verify", "agent-skills/test-driven-development", "ruflo-skills/verification-quality"]),
    (["refactor", "simplify", "clean"], ["agent-skills/code-simplification", "mattpocock/engineering/improve-codebase-architecture"]),
    (["ship", "deploy", "release", "launch"], ["agent-skills/shipping-and-launch", "worktree-task"]),
    (["build", "create", "implement", "write", "scaffold"], ["github-search", "build-and-verify"]),
    (["skill", "template", "catalog"], ["ruflo-skills/skill-builder", "agent-skills/context-engineering"]),
    (["role", "agent", "coordinator", "orchestrat"], ["agent-skills/planning-and-task-breakdown", "ruflo-skills/sparc-methodology"]),
]

# GOLDEN_RULES.md anti-patterns — warn if task contains these keywords
_ANTI_PATTERNS = [
    ("proxy", "anthropic_base_url", "wrap claude", "shell function.*claude"),  # Rule 13
    ("liveTurnTimeoutMs", "liveturn"),  # Rule 6
    ("bridge.*openclaw", "network.*bridge"),  # Rule 3
    ("gemini", "gemini.*fallback"),  # Rule 4 (ADR-004)
]
_ANTI_PATTERN_MESSAGES = {
    "proxy": "⛔ RULE 13: Never proxy Claude Code. Use jeanne-code (subprocess isolation) instead.",
    "anthropic_base_url": "⛔ RULE 13: Never set ANTHROPIC_BASE_URL system-wide. Broke Claude Code auth 2026-05-29.",
    "wrap claude": "⛔ RULE 13: Never wrap the claude command. Use jeanne-code instead.",
    "liveturn": "⛔ RULE 6: liveTurnTimeoutMs is permanently banned from openclaw.json.",
    "gemini": "⛔ ADR-004: Gemini free-tier must NOT be in any fallback chain — quota exhausts silently.",
}

# Vision pillars — auto-detect from task keywords
_VISION_TAGS = [
    (["memory", "recall", "session", "context", "redis", "chroma", "l3", "l4", "l5"], "Memory"),
    (["telegram", "openclaw", "dashboard", "interface", "voice", "mobile", "api"], "Interface"),
    (["self-improve", "train", "finetune", "autonomous", "weekly", "cron", "self-repair"], "Autonomy"),
    (["cost", "credit", "billing", "runpod", "vast", "free", "cheap"], "Cost"),
    (["jeanne", "persona", "identity", "consistent", "character"], "Identity"),
]

# Task title prefixes that trigger GitHub-first reminder (Rule 16)
_BUILD_PREFIXES = ("build:", "create:", "implement:", "add:", "write:", "scaffold:", "make:")


def layer0_skill_hints(query: str) -> str:
    """Return compact skill hints, doc-drift warning, vision tag, and anti-pattern alerts. Fast, local, no network."""
    query_lower = query.lower()
    lines = []

    # Anti-pattern check (GOLDEN_RULES — emitted first as BLOCKING warnings)
    for patterns in _ANTI_PATTERNS:
        for pattern in patterns:
            import re
            if re.search(pattern, query_lower):
                msg = _ANTI_PATTERN_MESSAGES.get(pattern.split(".*")[0], f"⛔ GOLDEN_RULES violation: '{pattern}'")
                lines.append(msg)

    # Vision tag (which [YOUR-AI-NAME]-VISION.md pillar does this serve?)
    vision_tags = []
    for keywords, pillar in _VISION_TAGS:
        if any(kw in query_lower for kw in keywords):
            vision_tags.append(pillar)
    if vision_tags:
        lines.append(f"Vision pillars served: {', '.join(vision_tags)} (see docs/vision/[YOUR-AI-NAME]-VISION.md)")
    else:
        lines.append("Vision pillar: not detected — add to task description which [YOUR-AI-NAME]-VISION.md goal this serves")

    # Skill hints
    matched = set()
    for keywords, skills in _SKILL_HINTS:
        if any(kw in query_lower for kw in keywords):
            matched.update(skills)
    if not matched:
        matched = {"claim-task", "worktree-task", "build-and-verify"}

    lines.append("Relevant skills:")
    for skill in sorted(matched):
        lines.append(f"  load: python3 {OPS}/skill_loader.py load {skill}")
    lines.append(f"  all skills: python3 {OPS}/skill_loader.py list")

    # Doc-drift reminder
    lines.append("Doc-drift check (run before closing task):")
    lines.append(f"  bash /usr/local/bin/jeanne-doc-drift-scan \"{query[:40]}\" --strict")

    return "\n".join(lines)


def run(args: list, timeout: int = 15) -> tuple[int, str]:
    """Run subprocess, return (returncode, stdout+stderr)."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, f"TIMEOUT after {timeout}s"
    except FileNotFoundError as e:
        return 1, f"NOT FOUND: {e}"


def layer4_codegraph(query: str) -> str:
    code, out = run(["python3", f"{OPS}/codegraph_adapter.py", "context", query])
    if code == 0 and out:
        return out[:MAX_CHARS_PER_LAYER]
    return ""


def layer3_claude_mem(query: str, task_type: str = "", scope: str = "") -> str:
    # Append task_type and scope to query for relevance filtering (V2 governance)
    scoped_query = query
    if task_type:
        scoped_query = f"{query} [task_type:{task_type}]"
    if scope:
        scoped_query = f"{scoped_query} [scope:{scope}]"
    code, out = run(["python3", f"{OPS}/claude_mem_adapter.py", "context", scoped_query])
    if code == 0 and out:
        return out[:MAX_CHARS_PER_LAYER]
    return ""


def layer6_github_patterns(query: str) -> str:
    """Layer 6: Search repo-intelligence/patterns/ and reference-repos/ for relevant patterns."""
    patterns_dir = f"{PROJECT_CTO}/repo-intelligence/patterns"
    refs_dir = f"{PROJECT_CTO}/repo-intelligence/reference-repos"
    query_words = set(query.lower().split())

    # Keyword → pattern directory mapping
    _PATTERN_MAP = {
        "voice": ["voice-pipeline"],
        "tts": ["voice-pipeline"],
        "stt": ["voice-pipeline"],
        "piper": ["voice-pipeline"],
        "speech": ["voice-pipeline"],
        "memory": ["memory-architecture"],
        "chromadb": ["memory-architecture"],
        "retrieval": ["memory-architecture"],
        "l3": ["memory-architecture"],
        "chat": ["chat-ux"],
        "conversation": ["chat-ux"],
        "session": ["chat-ux"],
        "routing": ["local-model-routing"],
        "inference": ["local-model-routing"],
        "context": ["local-model-routing"],
        "ollama": ["local-model-routing"],
        "agent": ["agent-orchestration"],
        "task": ["agent-orchestration"],
        "orchestrat": ["agent-orchestration"],
        "plugin": ["plugin-systems"],
        "module": ["plugin-systems"],
        "tool": ["plugin-systems"],
    }

    # Reference repo keyword → repo slug mapping
    _REF_MAP = {
        "voice": ["open-webui", "lobe-chat"],
        "tts": ["open-webui", "lobe-chat"],
        "memory": ["claude-mem"],
        "chat": ["lobe-chat", "librechat"],
        "routing": ["open-webui", "librechat"],
        "agent": ["openhands", "langgraph"],
        "task": ["openhands"],
        "repo": ["repograph", "codegraphcontext"],
        "code": ["repograph", "codegraphcontext", "continue-dev"],
        "workflow": ["flowise"],
    }

    import glob as glob_module

    matched_patterns = []
    matched_refs = []

    for word in query_words:
        for keyword, dirs in _PATTERN_MAP.items():
            if keyword in word or word in keyword:
                for d in dirs:
                    pattern_glob = f"{patterns_dir}/{d}/*.md"
                    for f in glob_module.glob(pattern_glob):
                        if f not in matched_patterns and not f.endswith('README.md'):
                            matched_patterns.append(f)
        for keyword, refs in _REF_MAP.items():
            if keyword in word or word in keyword:
                for ref in refs:
                    ref_file = f"{refs_dir}/{ref}/analysis.md"
                    if ref_file not in matched_refs and os.path.exists(ref_file):
                        matched_refs.append(ref_file)

    output_lines = []
    # Include up to 2 pattern files (first 300 chars each)
    for pf in matched_patterns[:2]:
        try:
            with open(pf) as f:
                content = f.read()[:300]
            pname = os.path.basename(pf).replace('.md', '')
            output_lines.append(f"[PATTERN: {pname}]\n{content}")
        except OSError:
            pass

    # Include up to 2 ref repo summaries (first 200 chars each)
    for rf in matched_refs[:2]:
        try:
            with open(rf) as f:
                lines = f.readlines()
            # Extract first 5 lines after the header
            summary = "".join(lines[3:8])[:200]
            rname = os.path.basename(os.path.dirname(rf))
            output_lines.append(f"[REF: {rname}]\n{summary}")
        except OSError:
            pass

    # Enhancement: Call github_ref_injector for task-aware suggestions (Task 1309)
    try:
        injector_path = f"{OPS}/github_ref_injector.py"
        if os.path.exists(injector_path):
            # Try to extract task context from environment or use query
            task_title = os.environ.get('PROJECT_TASK_TITLE', query[:50])
            task_layer = os.environ.get('PROJECT_TASK_LAYER', 'unassigned')

            code, injector_out = run([
                'python3', injector_path, task_title, task_layer, '--top', '2'
            ], timeout=3)

            if code == 0 and injector_out:
                try:
                    suggestions = json.loads(injector_out)
                    if suggestions.get('suggestions'):
                        suggestion_lines = []
                        for repo in suggestions['suggestions'][:2]:
                            line = f"- {repo['name']} (priority: {repo['priority']})"
                            if repo.get('url'):
                                line += f": {repo['url']}"
                            suggestion_lines.append(line)
                        if suggestion_lines:
                            output_lines.append(f"[GITHUB REFS - Task 1309]\n" + "\n".join(suggestion_lines))
                except json.JSONDecodeError:
                    pass  # Injector output not JSON, skip
    except Exception:
        pass  # github_ref_injector is optional enhancement

    return "\n\n".join(output_lines)[:MAX_CHARS_PER_LAYER] if output_lines else ""


def layer5_decision_log() -> str:
    code, out = run(
        ["git", "-C", PROJECT_CTO, "log", "--oneline", f"-{MAX_ADR_LOG_LINES}",
         "docs/architecture/decision-log.md"],
        timeout=10,
    )
    if code == 0 and out:
        return out
    return ""


def layer5_golden_rules_excerpt() -> str:
    """Return the one-line summary section of GOLDEN_RULES.md."""
    path = f"{PROJECT_CTO}/GOLDEN_RULES.md"
    try:
        with open(path) as f:
            lines = f.readlines()
        # Return first 20 lines (the summary rules)
        return "".join(lines[:20]).strip()[:MAX_CHARS_PER_LAYER]
    except OSError:
        return ""


def inject(query: str, layers: list = None, as_json: bool = False,
           task_type: str = "", scope: str = "") -> dict:
    if layers is None:
        layers = ["l0", "l4", "l3", "l5", "l6"]

    results = {}

    if "l0" in layers:
        results["layer0_skills"] = layer0_skill_hints(query)

    if "l4" in layers:
        results["layer4_codegraph"] = layer4_codegraph(query)

    if "l3" in layers:
        results["layer3_claude_mem"] = layer3_claude_mem(query, task_type=task_type, scope=scope)

    if "l5" in layers:
        results["layer5_decision_log"] = layer5_decision_log()
        results["layer5_golden_rules"] = layer5_golden_rules_excerpt()

    if "l6" in layers:
        results["layer6_github_patterns"] = layer6_github_patterns(query)

    return results


def format_context(query: str, results: dict) -> str:
    lines = [
        "=== INJECTED MEMORY CONTEXT ===",
        f"Query: {query}",
        "",
    ]

    # Task 1648: AGENTS-V3 Specialist routing (Phase 5A-2)
    # Select best-fit specialist persona for this task and inject their prompt
    if HAS_SPECIALIST_ROUTER:
        try:
            specialist, confidence, matched = detect_specialist(query)
            specialist_prompt = format_specialist_prompt(specialist, query, confidence)
            if specialist_prompt:
                lines.append(specialist_prompt)
        except Exception:
            pass  # Specialist routing is optional; missing module is non-fatal

    # Task 1657-1658: L3b Peer-centric reasoning with semantic matching (Phase 5B-1+2)
    # Query peer representations for Billy preferences and agent patterns
    if HAS_PEER_REASONING:
        try:
            pr = PeerReasoning()
            # Query Billy's preferences for this task context with semantic scoring
            billy_result = pr.query_peer("billy", query, threshold=0.20, include_scores=True)
            if billy_result and (billy_result["preferences"] or billy_result["knowledge"] or billy_result["patterns"]):
                formatted = format_peer_context(billy_result, include_confidence=True)
                if formatted:
                    lines.append(formatted)
                    lines.append("")

            # For infrastructure/agent tasks: also query relevant agent
            # Detect task scope and query appropriate specialist agent
            query_lower = query.lower()
            agent_hints = {
                "backend": ["backend-agent", "api", "service", "route"],
                "infrastructure": ["infrastructure-agent", "docker", "systemd", "deploy"],
                "frontend": ["frontend-agent", "react", "dashboard", "ui"],
                "memory": ["memory-agent", "postgres", "redis", "chroma"],
            }

            for agent_id, keywords in agent_hints.items():
                if any(kw in query_lower for kw in keywords):
                    agent_result = pr.query_peer(agent_id, query, threshold=0.20, include_scores=True)
                    if agent_result and agent_result.get("confidence", 0) >= 0.3:
                        formatted = format_peer_context(agent_result, include_confidence=True)
                        if formatted:
                            lines.append(formatted)
                            lines.append("")
                    break

            pr.close()
        except Exception as e:
            logger.debug(f"Peer reasoning optional feature unavailable: {e}")
            pass  # Peer reasoning is optional; missing/unavailable DB is non-fatal

    # Task 1663: Memory recall — inject relevant past experiences from session logs (Phase 5C-4)
    # Autonomous learning: let agents learn from completed sessions
    if HAS_MEMORY_RECALL:
        try:
            recall = MemoryRecall()
            if recall.health_check():
                # Extract task type from query if possible (IMPLEMENT, FIX, MIGRATE, etc.)
                task_type = None
                for prefix in ["IMPLEMENT:", "FIX:", "MIGRATE:", "BUILD:", "DESIGN:", "DEBUG:"]:
                    if prefix in query:
                        task_type = prefix.rstrip(":")
                        break

                memories = recall.recall_for_task(query, task_type=task_type, n_results=3)
                if memories:
                    formatted = format_memory_context(memories, max_length=400)
                    if formatted:
                        lines.append(formatted)
                        lines.append("")
        except Exception as e:
            logger.debug(f"Memory recall optional feature unavailable: {e}")
            pass  # Memory recall is optional; missing/unavailable ChromaDB is non-fatal

    # Layer discipline hint — guides which layers to query next time
    _LAYER_GUIDE = {
        "code": "l0,l4,l3",
        "infra": "l0,l5,l3",
        "memory": "l0,l3,l2",
        "arch": "l0,l5,l3",
        "doc": "l0,l5",
    }
    q_lower = query.lower()
    rec_layers = next(
        (v for k, v in _LAYER_GUIDE.items() if k in q_lower), "l0,l4,l3,l5"
    )
    lines.append(f"[TOKEN BUDGET: ≤500 tokens | use --layers {rec_layers} for this query type]")
    lines.append("")

    # Vision Alignment Reminder — mandatory reading prompt (task 1008)
    lines.append("[VISION ALIGNMENT REMINDER — read before starting]")
    lines.append("5 Pillars: Memory | Identity | Autonomy | Interface | Intelligence")
    lines.append("Directive: docs/vision/[YOUR-AI-NAME]-PLATFORM-MASTER-DIRECTIVE.md")
    lines.append("Drift prevention: docs/governance/TASK-DRIFT-PREVENTION.md")
    # Determine pillar alignment from query keywords
    _PILLAR_KEYWORDS = {
        "Memory": ["memory", "context", "embed", "recall", "retrieval", "chroma", "redis", "l3"],
        "Identity": ["identity", "persona", "profile", "character", "voice", "jeanne"],
        "Autonomy": ["agent", "task", "autonom", "orchestrat", "worker", "cron", "schedule"],
        "Interface": ["ui", "dashboard", "chat", "telegram", "interface", "frontend", "react"],
        "Intelligence": ["model", "ollama", "inference", "llm", "ai", "routing", "venzarai"],
    }
    matched_pillars = [pillar for pillar, kws in _PILLAR_KEYWORDS.items() if any(k in q_lower for k in kws)]
    if matched_pillars:
        lines.append(f"Pillar alignment for this task: {', '.join(matched_pillars)}")
    lines.append("")

    # Rule 16: GitHub-first reminder for BUILD tasks
    if query.lower().startswith(_BUILD_PREFIXES):
        lines.append("[RULE 16 — GITHUB-FIRST REMINDER]")
        lines.append("Before implementing from scratch: search GitHub for existing solutions.")
        lines.append("  1. Load: python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load github-search")
        lines.append("  2. Follow SKILL.md protocol — in most cases copy code structure")
        lines.append("  3. Security audit any cloned repo: bash ops/security/github-import-audit.sh <dir>")
        lines.append("")

    if results.get("layer0_skills"):
        lines.append("[L0 SKILL HINTS — load before starting]")
        lines.append(results["layer0_skills"])
        lines.append("")

    if results.get("layer4_codegraph"):
        lines.append("[L4 CODE INTELLIGENCE — codegraph]")
        lines.append(results["layer4_codegraph"])
        lines.append("")

    if results.get("layer3_claude_mem"):
        lines.append("[L3 SEMANTIC MEMORY — claude-mem]")
        lines.append(results["layer3_claude_mem"])
        lines.append("")

    if results.get("layer5_decision_log"):
        lines.append("[L5 INSTITUTIONAL — recent ADR commits]")
        lines.append(results["layer5_decision_log"])
        lines.append("")

    if results.get("layer5_golden_rules"):
        lines.append("[L5 GOLDEN RULES — top constraints]")
        lines.append(results["layer5_golden_rules"])
        lines.append("")

    if results.get("layer6_github_patterns"):
        lines.append("[L6 GITHUB PATTERNS — repo-intelligence matches]")
        lines.append(results["layer6_github_patterns"])
        lines.append("")

    populated = sum(1 for v in results.values() if v)
    if populated == 0:
        lines.append("(no context retrieved — all layers unavailable or empty)")

    lines.append("================================")
    output = "\n".join(lines)
    # Hard cap: truncate to MAX_TOTAL_CHARS to enforce ≤500 token budget
    if len(output) > MAX_TOTAL_CHARS:
        output = output[:MAX_TOTAL_CHARS] + f"\n[TRUNCATED — {len(output)} chars → {MAX_TOTAL_CHARS} chars limit]\n================================"
    return output


def create_context_injection_finding(query: str, layers_populated: int, total_chars: int):
    """REAL: Export context injection event → findings"""
    if not HAS_FINDINGS:
        return
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-inject-{hash(query) % 1000000}-{int(datetime.now().timestamp())}",
            service="inject-context",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Context injected: query={query[:50]}, layers={layers_populated}, chars={total_chars}",
            evidence=[{"type": "context_injection", "text": f"Query: {query}, Layers populated: {layers_populated}, Total chars: {total_chars}"}],
            related_metrics={"query": query, "layers_populated": layers_populated, "total_chars": total_chars}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Task description or search query")
    parser.add_argument(
        "--layers",
        default="l4,l3,l5",
        help="Comma-separated layer list: l1,l2,l3,l4,l5 (default: l4,l3,l5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output as JSON dict instead of formatted text",
    )
    parser.add_argument(
        "--task-type",
        default="",
        help="Task type for L3 scope filtering: build|fix|audit|doc|infra",
    )
    parser.add_argument(
        "--scope",
        default="",
        help="Comma-separated scope tags for L3 filtering: voice,memory,v8,infra,etc.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview which memory layers will be queried without loading context (blast-radius check, task 1712)",
    )
    args = parser.parse_args()

    layers = [l.strip().lower() for l in args.layers.split(",")]

    # Dry-run: show blast-radius preview without loading context (task 1712)
    if args.dry_run:
        print("=== Memory Pre-Flight Blast-Radius Check ===")
        print(f"Query: {args.query[:80]}")
        print(f"Layers to query: {layers}")
        print(f"Task type: {args.task_type or 'unspecified'}")
        print(f"Scope: {args.scope or 'all'}")
        print("")
        layer_descriptions = {
            "l0": "L0 Skills — local skill catalog hints (no network)",
            "l1": "L1 Redis — runtime state cache",
            "l2": "L2 PostgreSQL — structured facts",
            "l3": "L3 ChromaDB — semantic engineering observations (claude-mem :37877)",
            "l4": "L4 CodeGraph — code symbols and call graph",
            "l5": "L5 Git — recent ADRs from decision-log.md",
            "l6": "L6 Patterns — repo-intelligence patterns and reference repos",
        }
        for layer in layers:
            desc = layer_descriptions.get(layer, f"{layer} — unknown layer")
            print(f"  WILL QUERY: {desc}")
        print("")
        print("Dry-run complete. No context loaded. Run without --dry-run to inject context.")
        return 0

    results = inject(args.query, layers, task_type=args.task_type, scope=args.scope)

    # Export context injection event as finding
    layers_populated = sum(1 for v in results.values() if v)
    output_text = format_context(args.query, results)
    create_context_injection_finding(args.query, layers_populated, len(output_text))

    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        print(output_text)

    # Exit 0 always — missing layers are non-fatal
    return 0


if __name__ == "__main__":
    sys.exit(main())
