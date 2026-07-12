# Protocol: Memory Injection at Task Claim

**Protocol:** memory-injection  
**Version:** 2.0  
**Last Updated:** 2026-05-28  
**Supersedes:** v1.0 (claude-mem-only model)

---

## Purpose

Agents inject relevant memory context when claiming a task, before doing any work. Context is drawn from all 5 memory layers — not just claude-mem. This ensures the agent has structural, semantic, and institutional knowledge relevant to the task domain.

Full architecture: `docs/architecture/MEMORY_ARCHITECTURE.md`  
Layer write/read rules: `agents/protocols/memory-governance.md`

---

## 5-Layer Injection Order

At task claim time, query layers in this order (fastest → richest):

| Step | Layer | Tool | Query |
|------|-------|------|-------|
| 1 | L4 Code Intelligence | `codegraph_adapter.py context` | Task description / affected symbol |
| 2 | L3 Semantic Memory | `claude_mem_adapter.py context` | Task description + tags |
| 3 | L5 Institutional | `git log docs/architecture/decision-log.md` | Scan ADRs for relevant decisions |
| 4 | L2 Structured Truth | `psql` query for relevant config/state | Only if task touches system config |
| 5 | L1 Runtime | `redis-cli` | Only if task touches live session state |

---

## When to Apply

At task claim time, before starting any work:
1. Read task description and tags from the JSON file
2. Run multi-layer injection (Steps 1–3 mandatory, Steps 4–5 only if relevant)
3. Load results into working context
4. Proceed with task

---

## Implementation

```python
import subprocess
import json

def inject_context(task_description: str, task_tags: list = None) -> dict:
    """
    Query all 5 memory layers for context relevant to a task.
    Returns dict with results per layer. Layers that fail return empty string.
    """
    query = task_description
    if task_tags:
        query = f"{task_description} {' '.join(task_tags)}"

    results = {}

    # Layer 4: Code Intelligence (codegraph) — always first
    cg = subprocess.run(
        ["python3", "/opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py", "context", task_description],
        capture_output=True, text=True, timeout=15
    )
    results["layer4_codegraph"] = cg.stdout.strip() if cg.returncode == 0 else ""

    # Layer 3: Semantic Memory (claude-mem) — engineering observations
    mem = subprocess.run(
        ["python3", "/opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py", "context", query],
        capture_output=True, text=True, timeout=30
    )
    results["layer3_claude_mem"] = mem.stdout.strip() if mem.returncode == 0 else ""

    # Layer 5: Institutional (decision log scan)
    adr = subprocess.run(
        ["git", "-C", "/opt/YOUR-PROJECT", "log", "--oneline", "-20",
         "docs/architecture/decision-log.md"],
        capture_output=True, text=True, timeout=10
    )
    results["layer5_decision_log"] = adr.stdout.strip() if adr.returncode == 0 else ""

    return results


def format_context_for_agent(results: dict) -> str:
    """Format multi-layer context as a readable block for agent consumption."""
    lines = ["=== INJECTED MEMORY CONTEXT ==="]

    if results.get("layer4_codegraph"):
        lines.append("\n[L4 CODE INTELLIGENCE]")
        lines.append(results["layer4_codegraph"])

    if results.get("layer3_claude_mem"):
        lines.append("\n[L3 SEMANTIC MEMORY]")
        lines.append(results["layer3_claude_mem"])

    if results.get("layer5_decision_log"):
        lines.append("\n[L5 INSTITUTIONAL — recent ADR commits]")
        lines.append(results["layer5_decision_log"])

    lines.append("==============================")
    return "\n".join(lines)


# Usage at task start:
# task = {"description": "Fix VenzariAI Router routing timeout", "tags": ["venzarai-router", "routing"]}
# ctx = inject_context(task["description"], task.get("tags", []))
# print(format_context_for_agent(ctx))
```

---

## Bash Wrapper

```bash
#!/bin/bash
# inject-context.sh — 5-layer memory injection at task claim
# Usage: source ops/agent/inject-context.sh "task description" [tag1 tag2 ...]

TASK_DESC="$1"
shift
TAGS="${*}"
QUERY="$TASK_DESC $TAGS"

echo "=== INJECTED MEMORY CONTEXT ==="

# L4: Code Intelligence
echo ""
echo "[L4 CODE INTELLIGENCE]"
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py context "$TASK_DESC" 2>/dev/null || echo "(unavailable)"

# L3: Semantic Memory
echo ""
echo "[L3 SEMANTIC MEMORY]"
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py context "$QUERY" 2>/dev/null || echo "(unavailable)"

# L5: Decision Log
echo ""
echo "[L5 INSTITUTIONAL — recent ADRs]"
git -C /opt/YOUR-PROJECT log --oneline -10 docs/architecture/decision-log.md 2>/dev/null || echo "(unavailable)"

echo "================================"
```

---

## Rules

1. L4 (codegraph) is **mandatory** for any task touching code — run it first, always
2. L3 (claude-mem) is **mandatory** — if the service is down, log the failure and proceed
3. L5 (decision log) takes 1 second and is always worth running — do not skip
4. L2 (postgres) and L1 (redis) are **optional** — only query if the task domain requires it
5. Memory injection adds context — it never blocks task start
6. If relevant L3/L5 context is found, cite it in the completion evidence string
7. Write new memory to L3 after completing: `claude_mem_adapter.py write "<observation>"`
8. If an architectural decision was made during the task → write to L5 (decision-log.md ADR)

---

## What NOT to do

- Do NOT write ephemeral state (current file contents, process PIDs) to L3
- Do NOT query L1/L2 "just in case" — only when structurally relevant
- Do NOT rely solely on L3 for code structure — codegraph (L4) is authoritative for code
- Do NOT write contradictory observations to L3 — check existing entries first with `query`

---

## Related

- `docs/architecture/MEMORY_ARCHITECTURE.md` — Full 5-layer specification
- `agents/protocols/memory-governance.md` — Layer write/read rules + forbidden patterns
- `ops/agent/claude_mem_adapter.py` — L3 adapter
- `ops/agent/codegraph_adapter.py` — L4 adapter
- `agents/protocols/evidence-contract.md` — How to write completion evidence
- `docs/integrations/claude-mem-deployment.md` — claude-mem service details
