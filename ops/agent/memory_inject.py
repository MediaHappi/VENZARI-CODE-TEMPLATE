# DEPRECATED 2026-05-27 — Use claude-mem adapter instead
# Replacement: ops/agent/claude_mem_adapter.py → POST http://localhost:37877/memory
# Delete after: 2026-06-27
# See: docs/integrations/codegraph-deployment.md and ops/agent/DEPRECATION_ROADMAP.md
#!/usr/bin/env python3
"""
[YOUR-AI-NAME] Engineering Memory — Task-Claim Context Injection (Progressive Disclosure)
Queries ChromaDB for relevant past observations when an agent claims a task.

Usage:
  python3 memory_inject.py "<task title or description>" [--n 5] [--expand 2]
  python3 memory_inject.py "fix LiteLLM warm chain not using Ollama"

The 3-layer progressive disclosure protocol:
  Layer 1 (always): Top-N obs_index entries — compact summaries (~50 tokens each)
  Layer 2 (selective): Top-M full obs_detail entries — only for the most relevant IDs
  Layer 3 (on demand): Raw detail for a specific obs_id — use memory_query.py expand <id>

Output is a formatted markdown string suitable for prepending to an agent's task context.
Token cost is reported at the end (approximate).

Exit codes:
  0 — success (observations found and printed)
  1 — ChromaDB unreachable (graceful — agent should continue without memory)
  2 — other error
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

CHROMA_HOSTS = [
    "http://127.0.0.1:8001",   # Local VPS (Venzari VPS)
    "http://127.0.0.1:8001",   # Fallback
]


def create_memory_injection_finding(task_query: str, obs_count: int, success: bool):
    """REAL: Export memory injection event → findings"""
    if not HAS_FINDINGS:
        return
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-mem-inject-{hash(task_query) % 1000000}-{int(datetime.now().timestamp())}",
            service="memory-inject",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Memory injected: {task_query[:60]}, {obs_count} obs" if success else f"Memory injection failed: {task_query[:60]}",
            evidence=[{"type": "memory_injection", "text": f"Query: {task_query}, Observations: {obs_count}, Success: {success}"}],
            related_metrics={"query": task_query, "obs_count": obs_count, "success": success}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def get_chroma_client():
    try:
        import chromadb
    except ImportError:
        return None, None
    for host in CHROMA_HOSTS:
        try:
            import urllib.request
            urllib.request.urlopen(f"{host}/api/v2/heartbeat", timeout=3)
            from urllib.parse import urlparse
            p = urlparse(host)
            client = chromadb.HttpClient(host=p.hostname, port=p.port)
            client.heartbeat()
            return client, host
        except Exception:
            continue
    return None, None


def inject_context(task_query: str, n_index: int = 5, n_expand: int = 2) -> str:
    """
    Query ChromaDB for relevant past observations.
    Returns a formatted markdown string or an empty string if ChromaDB is unreachable.
    """
    client, host = get_chroma_client()
    if client is None:
        return ""  # Graceful degradation — caller continues without memory

    try:
        index_col = client.get_or_create_collection("jeanne_obs_index")
        detail_col = client.get_or_create_collection("jeanne_obs_detail")
    except Exception as e:
        print(f"[memory_inject] ChromaDB collection error: {e}", file=sys.stderr)
        return ""

    count = index_col.count()
    if count == 0:
        return ""  # No observations yet — first agent session

    # Layer 1: Search index (compact summaries only)
    try:
        index_results = index_col.query(
            query_texts=[task_query],
            n_results=min(n_index, count),
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print(f"[memory_inject] Index query failed: {e}", file=sys.stderr)
        return ""

    if not index_results["ids"][0]:
        return ""

    ids = index_results["ids"][0]
    docs = index_results["documents"][0]
    metas = index_results["metadatas"][0]
    distances = index_results["distances"][0]

    # Layer 2: Expand top-N most relevant to full detail
    lines = ["## Relevant Past Observations (from Engineering Memory)\n"]
    lines.append(f"*Query: \"{task_query}\" — {len(ids)} index matches, {n_expand} expanded*\n")

    expanded_count = 0
    for i, (obs_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, distances)):
        relevance = max(0.0, 1.0 - dist)  # distance → relevance score
        agent = meta.get("agent", "unknown")
        obs_type = meta.get("type", "observation")
        ts = meta.get("ts", "")
        tags_raw = meta.get("tags", "[]")
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        except Exception:
            tags = []
        tags_str = " ".join(f"#{t}" for t in tags) if tags else ""

        # Always show index entry (compact)
        lines.append(f"### [{obs_id}] {obs_type.upper()} — relevance: {relevance:.2f}")
        lines.append(f"*Agent: {agent} | {ts[:10] if ts else 'unknown date'} {tags_str}*")
        lines.append(f"> {doc}")
        lines.append("")

        # Expand top-N to full detail
        if i < n_expand and expanded_count < n_expand:
            try:
                detail_results = detail_col.get(
                    ids=[obs_id],
                    include=["documents"]
                )
                if detail_results["documents"]:
                    detail_text = detail_results["documents"][0]
                    lines.append("**Full detail:**")
                    lines.append(f"```\n{detail_text[:1500]}\n```")
                    lines.append("")
                    expanded_count += 1
            except Exception:
                pass  # detail expansion is optional

    # Approximate token cost (rough: 1 token ≈ 4 chars)
    output = "\n".join(lines)
    approx_tokens = len(output) // 4
    lines.append(f"\n*Memory injection cost: ~{approx_tokens} tokens ({len(ids)} index + {expanded_count} expanded)*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Inject relevant memory context for a task")
    parser.add_argument("query", help="Task title or description to search for")
    parser.add_argument("--n", type=int, default=5, help="Number of index results (default: 5)")
    parser.add_argument("--expand", type=int, default=2, help="Number of results to expand to full detail (default: 2)")
    parser.add_argument("--quiet", action="store_true", help="Suppress stderr messages")
    args = parser.parse_args()

    result = inject_context(args.query, n_index=args.n, n_expand=args.expand)

    if result:
        print(result)
        # Export successful memory injection finding
        obs_count = result.count("Index observation") if "Index observation" in result else 0
        create_memory_injection_finding(args.query, obs_count, True)
        sys.exit(0)
    else:
        if not args.quiet:
            print("[memory_inject] ChromaDB unreachable or no observations found — continuing without memory context",
                  file=sys.stderr)
        # Export failed memory injection finding
        create_memory_injection_finding(args.query, 0, False)
        sys.exit(1)


if __name__ == "__main__":
    main()
