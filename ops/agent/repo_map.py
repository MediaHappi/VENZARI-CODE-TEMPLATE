#!/usr/bin/env python3
"""
Intelligent, auto-updating repo map for YOUR-PROJECT (task O0000000005).

GITHUB RESEARCH FIRST: read Aider's actual repomap.py in full before designing this. See
docs/governance/REPO-MAP-RESEARCH.md for exactly what was read and what was copied
conceptually vs. adapted for this repo's own requirements.

Adapts Aider's file-level PageRank ranking on top of codegraph's already-parsed symbol
graph (.codegraph/codegraph.db) instead of re-implementing tree-sitter parsing: reads
codegraph's nodes/edges tables directly, builds a file-level directed graph weighted by
call/import edge counts (Aider's sqrt(num_refs) damping), applies a penalty multiplier for
archived/historical paths (a real gap in codegraph's own raw ranking, confirmed during
research -- see REPO-MAP-RESEARCH.md), and runs networkx.pagerank.

Usage:
  python3 repo_map.py context "<task title or query>"  -- ranked, token-budgeted map
  python3 repo_map.py refresh                           -- force a codegraph sync
  python3 repo_map.py verify                             -- sanity-check the pipeline
"""
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_DIR / ".codegraph" / "codegraph.db"
CODEGRAPH_BIN = "/home/billy/.local/bin/codegraph"

sys.path.insert(0, str(Path(__file__).parent))

# Paths that are structurally present in the graph but should never dominate the ranking --
# archived/dead code, vendored copies, and per-task worktree checkouts (which duplicate the
# whole live tree under .worktrees/<id>/ while a task is in progress).
PENALIZED_PATH_PREFIXES = {
    "docs/archive/": 0.01,
    ".worktrees/": 0.01,
    "agents/vendors/": 0.1,
}

REFRESH_STALE_SECONDS = 3600


def _penalty_for(file_path: str) -> float:
    for prefix, mul in PENALIZED_PATH_PREFIXES.items():
        if file_path.startswith(prefix):
            return mul
    return 1.0


def index_age_seconds() -> float:
    if not DB_PATH.exists():
        return float("inf")
    return time.time() - DB_PATH.stat().st_mtime


def ensure_fresh(max_age_seconds: int = REFRESH_STALE_SECONDS) -> bool:
    """Run `codegraph sync` if the index is older than max_age_seconds. Returns True if a
    sync ran. Cheap to call often -- codegraph sync only re-parses changed files (confirmed:
    a routine run reported 12 modified out of 697 total, not a full re-index), matching
    Aider's "just redo it, it's cheap" refresh philosophy rather than a git hook."""
    if index_age_seconds() <= max_age_seconds:
        return False
    subprocess.run([CODEGRAPH_BIN, "sync"], capture_output=True, text=True, cwd=str(REPO_DIR), timeout=120)
    return True


def _connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"codegraph index not found at {DB_PATH} -- run `codegraph init -i` first")
    return sqlite3.connect(str(DB_PATH))


def build_file_graph(conn) -> "networkx.DiGraph":
    import networkx as nx
    import math

    cur = conn.cursor()
    cur.execute("SELECT id, file_path FROM nodes")
    node_file = {nid: fp for nid, fp in cur.fetchall()}

    cur.execute("SELECT source, target, kind FROM edges WHERE kind IN ('calls', 'imports', 'extends', 'implements', 'instantiates', 'references')")
    edge_rows = cur.fetchall()

    G = nx.DiGraph()
    for fp in set(node_file.values()):
        G.add_node(fp)

    pair_counts = {}
    for source, target, kind in edge_rows:
        src_fp = node_file.get(source)
        dst_fp = node_file.get(target)
        if not src_fp or not dst_fp or src_fp == dst_fp:
            continue
        pair_counts[(src_fp, dst_fp)] = pair_counts.get((src_fp, dst_fp), 0) + 1

    for (src_fp, dst_fp), count in pair_counts.items():
        weight = math.sqrt(count) * _penalty_for(dst_fp)
        G.add_edge(src_fp, dst_fp, weight=weight)

    return G


def rank_files(query: str = "", top_n: int = 30) -> list:
    """Returns [(file_path, rank_score), ...] sorted descending. `query` words that match a
    file's basename get PageRank personalization boost, mirroring Aider's mentioned_fnames."""
    conn = _connect()
    try:
        G = build_file_graph(conn)
    finally:
        conn.close()

    if G.number_of_nodes() == 0:
        return []

    query_words = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", (query or "").lower()))
    personalization = {}
    if query_words:
        for node in G.nodes:
            basename = Path(node).stem.lower()
            if basename in query_words or any(w in basename for w in query_words if len(w) >= 4):
                personalization[node] = 1.0

    pers_args = {}
    if personalization:
        total = sum(personalization.values())
        pers_args["personalization"] = {k: v / total for k, v in personalization.items()}
        pers_args["dangling"] = pers_args["personalization"]

    import networkx as nx
    try:
        ranked = nx.pagerank(G, weight="weight", **pers_args)
    except ZeroDivisionError:
        ranked = nx.pagerank(G, weight="weight")

    for fp in ranked:
        ranked[fp] *= _penalty_for(fp)

    return sorted(ranked.items(), key=lambda kv: kv[1], reverse=True)[:top_n]


def layer_for_path(file_path: str) -> str:
    parts = Path(file_path).parts
    if not parts:
        return "infrastructure"
    top = parts[0]
    mapping = {
        "ops": "infrastructure", "docs": "documentation", "system-map": "infrastructure",
        "agents": "orchestration", ".tasks": "orchestration",
    }
    if top in mapping:
        return mapping[top]
    if len(parts) > 1 and "memory" in parts[1].lower():
        return "memory"
    if len(parts) > 1 and "test" in parts[1].lower():
        return "testing"
    return "infrastructure"


def doc_for_layer(layer: str) -> list:
    try:
        from drift_scanner import parse_doc_matrix
        return parse_doc_matrix(layer)
    except Exception:
        return []


def build_map(query: str = "", top_n: int = 20, refresh: bool = True) -> str:
    if refresh:
        ensure_fresh()
    ranked = rank_files(query=query, top_n=top_n)
    lines = [f"## Repo Map{f' for: {query}' if query else ''}", ""]
    seen_docs = set()
    for file_path, score in ranked:
        layer = layer_for_path(file_path)
        lines.append(f"- `{file_path}` (rank {score:.4f}, layer: {layer})")
        for doc in doc_for_layer(layer):
            if doc not in seen_docs:
                seen_docs.add(doc)
    if seen_docs:
        lines.append("")
        lines.append("### Governing docs for ranked layers")
        for doc in sorted(seen_docs):
            lines.append(f"- {doc}")
    return "\n".join(lines)


def verify():
    if not Path(CODEGRAPH_BIN).is_file():
        print(f"ERROR: codegraph binary not found at {CODEGRAPH_BIN}")
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"ERROR: codegraph index not found at {DB_PATH}")
        sys.exit(1)
    ranked = rank_files(top_n=5)
    if not ranked:
        print("ERROR: rank_files() returned no results")
        sys.exit(1)
    print(f"OK: repo_map verified -- {len(ranked)} top files ranked, index age {index_age_seconds():.0f}s")
    for fp, score in ranked:
        print(f"  {score:.4f}  {fp}")


def main():
    if len(sys.argv) < 2:
        print("Usage: repo_map.py <context|refresh|verify> [query]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "verify":
        verify()
    elif cmd == "refresh":
        did = ensure_fresh(max_age_seconds=0)
        print(f"OK: refreshed" if did else "OK: already fresh")
    elif cmd == "context":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        print(build_map(query=query))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
