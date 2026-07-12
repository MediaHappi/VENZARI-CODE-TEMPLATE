#!/usr/bin/env python3
"""Persist task completion to ALL 5 memory layers.

Instead of depending on single memory layer, write to:
- L1: Redis (session cache, fast access)
- L2: PostgreSQL (semantic_facts, reasoning_decisions, episodic_sessions)
- L3: ChromaDB (vector embeddings for semantic search)
- L4: CodeGraph (code symbols and references via MCP)
- L5: Git/Archive (immutable record in version control)

Task completion succeeds if ANY layer succeeds.
Failures in individual layers do not block completion.
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Tuple

# Overridable via PROJECT_CTO_PATH for test isolation (2026-07-02) — matches
# advisor_manager.py's pattern. A FUNCTION, not a module-level constant: a
# constant freezes at first import, so setting the env var later in the same
# process would silently have no effect.
def _repo_dir() -> Path:
    """PROJECT_CTO_PATH wins if set (tests use this for isolation). Otherwise resolve
    relative to this script's own location, not a hardcoded '/opt/YOUR-PROJECT' -- the
    same class of bug found and fixed in state_archiver.py (task O0000000006) and
    advisor_orchestrator.py (task O0000000007): a hardcoded fallback made a worktree
    copy of the script silently operate on the main repo's files instead of its own."""
    env_path = os.environ.get('PROJECT_CTO_PATH')
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2]

def persist_to_l1_redis(task: Dict) -> Tuple[bool, str]:
    """L1: Redis — Fast session cache."""
    try:
        import redis

        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(redis_url)

        task_id = task.get('id')
        key = f"task:{task_id}:completion"

        completion_data = {
            'task_id': task_id,
            'completed_at': task.get('completed_at'),
            'summary': task.get('summary'),
            'evidence': task.get('evidence', '')[:200],
        }

        r.setex(key, 86400, json.dumps(completion_data))  # 24h TTL
        return True, "Redis L1"
    except Exception as e:
        return False, f"L1 Redis error: {e}"

def persist_to_l2_postgres(task: Dict, evidence: str, summary: str) -> Tuple[bool, str]:
    """L2: PostgreSQL — Semantic facts and reasoning decisions."""
    try:
        import psycopg2
        from psycopg2.extras import Json
        import time

        db_url = os.getenv('DATABASE_URL',
                          f"postgresql://{os.getenv('POSTGRES_USER', 'readykit')}:"
                          f"{os.getenv('POSTGRES_PASSWORD', 'readykit')}@"
                          f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
                          f"{os.getenv('POSTGRES_PORT', '5432')}/"
                          f"{os.getenv('POSTGRES_DB', 'venzarai_hub')}")

        # Retry for transient failures
        for attempt in range(3):
            try:
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()

                # Ensure schemas exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_facts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        content TEXT NOT NULL,
                        domain TEXT DEFAULT 'general',
                        source_task_id TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reasoning_decisions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        task_id TEXT NOT NULL,
                        reasoning TEXT,
                        choice_made TEXT,
                        category TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                # Insert to semantic_facts
                cur.execute("""
                    INSERT INTO semantic_facts (content, domain, source_task_id, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (f"{task.get('title')}: {summary}\nEvidence: {evidence[:500]}",
                      task.get('layer', 'general'), task.get('id'), datetime.now(timezone.utc)))

                # Insert to reasoning_decisions
                cur.execute("""
                    INSERT INTO reasoning_decisions (task_id, reasoning, choice_made, category, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (task.get('id'), summary, f"Completed {task.get('id')}",
                      task.get('layer', 'general'), datetime.now(timezone.utc)))

                conn.commit()
                cur.close()
                conn.close()
                return True, "PostgreSQL L2"

            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise

    except Exception as e:
        return False, f"L2 PostgreSQL error: {e}"

def persist_to_l3_chromadb(task: Dict, evidence: str, summary: str) -> Tuple[bool, str]:
    """L3: ChromaDB — Vector embeddings for semantic search."""
    try:
        import chromadb

        client = chromadb.HttpClient(host=os.getenv('CHROMADB_HOST', 'localhost'),
                                    port=int(os.getenv('CHROMADB_PORT', '8001')))

        collection = client.get_or_create_collection(name="task_completions")

        task_id = task.get('id')
        content = f"{task.get('title')}: {summary}\nEvidence: {evidence[:500]}"

        # ChromaDB's metadata schema rejects null values (task 1704, H-008 follow-up) --
        # persist_to_all_layers() is called mid-completion, before task['completed_at']
        # is stamped in the in-memory dict, so it's still None here for a real task
        # completion (only present when re-reading an already-completed task from disk,
        # which is why this bug was invisible when testing with post-completion task
        # dicts). Default missing values instead of passing None through.
        completed_at = task.get('completed_at') or datetime.now(timezone.utc).isoformat()
        layer = task.get('layer') or 'general'

        collection.add(
            ids=[task_id],
            documents=[content],
            metadatas=[{
                'layer': layer,
                'completed_at': completed_at,
            }]
        )

        return True, "ChromaDB L3"
    except Exception as e:
        return False, f"L3 ChromaDB error: {e}"

def persist_to_l4_codegraph(task: Dict) -> Tuple[bool, str]:
    """L4: CodeGraph — Code symbols and references.

    Task M0000000021 (2026-07-02): wired to the real, already-installed codegraph binary
    (colbymchenry/codegraph, a tree-sitter+SQLite CLI tool at ~/.local/bin/codegraph —
    NOT an MCP server, no Gmail/Drive/OAuth involvement anywhere in this codepath). The
    EG-004 stub above this comment (hardcoded return False) was written before this
    tool's adapter (ops/agent/codegraph_adapter.py) existed; it's real and working now,
    confirmed via `codegraph --version` and a live index file at .codegraph/codegraph.db.

    This is a real health check (binary responds, index file present), matching the
    pattern of every other layer here (L1/L2/L3/L5 all make a real call, not a keyword
    check) — same EG-004 principle still applies: this must be genuinely falsifiable,
    not a disguised unconditional True.
    """
    codegraph_bin = os.environ.get("CODEGRAPH_BIN", "/home/billy/.local/bin/codegraph")
    db_path = _repo_dir() / ".codegraph" / "codegraph.db"

    if not os.path.isfile(codegraph_bin):
        return False, f"CodeGraph L4: binary not found at {codegraph_bin}"
    if not db_path.is_file():
        return False, f"CodeGraph L4: index not found at {db_path}"

    try:
        import subprocess
        result = subprocess.run(
            [codegraph_bin, "--version"],
            capture_output=True, text=True, cwd=str(_repo_dir()), timeout=10,
        )
        if result.returncode != 0:
            return False, f"CodeGraph L4: binary check failed (exit {result.returncode}): {result.stderr.strip()[:200]}"
        return True, f"CodeGraph L4 ({result.stdout.strip()})"
    except Exception as e:
        return False, f"CodeGraph L4 error: {e}"

def persist_to_l5_git(task: Dict, evidence: str, summary: str) -> Tuple[bool, str]:
    """L5: Git/Archive — Immutable record in version control.
    EG-004: Actually commit archive to git for true immutability.

    Task M0000000023 (Codex Phase 5.6): this used to run `git add` and `git commit`
    without checking either subprocess's returncode, then unconditionally returned
    True/"committed" regardless of whether the commit actually happened. A failed
    commit (lock held, detached HEAD, hook rejection, not a git repo at all) meant
    task completion could believe durable L5 memory succeeded when only an
    UNCOMMITTED loose file existed -- exactly the false-positive
    `persist_to_all_layers()`'s `durable_succeeded` field (task I0000000044) exists
    to prevent, undermined at its own source. Now: L5 only reports success when
    `git commit` genuinely exits 0, or the specific benign "nothing to commit"
    case (the exact content is already committed from a prior identical persist).
    """
    try:
        import subprocess

        task_id = task.get('id')
        archive_dir = _repo_dir() / '.memory_archive'
        archive_dir.mkdir(exist_ok=True)

        completion_record = {
            'task_id': task_id,
            'title': task.get('title'),
            'summary': summary,
            'evidence': evidence[:500],
            'layer': task.get('layer'),
            'completed_at': task.get('completed_at'),
        }

        record_file = archive_dir / f"{task_id}.json"
        with open(record_file, 'w') as f:
            json.dump(completion_record, f, indent=2)

        # EG-004 / M0000000023: actually verify the commit happened before
        # reporting durable success.
        try:
            add_proc = subprocess.run(
                ['git', '-C', str(_repo_dir()), 'add', str(record_file)],
                capture_output=True, timeout=5, text=True,
            )
            if add_proc.returncode != 0:
                return False, f"L5 Git/Archive: git add failed (exit {add_proc.returncode}): {add_proc.stderr.strip()[:200]}"

            commit_proc = subprocess.run(
                ['git', '-C', str(_repo_dir()), 'commit', '-m', f'archive: task {task_id} completion record'],
                capture_output=True, timeout=5, text=True,
            )
            commit_output = (commit_proc.stdout + commit_proc.stderr).lower()
            if commit_proc.returncode == 0:
                return True, "Git/Archive L5 (committed to .memory_archive)"
            if "nothing to commit" in commit_output:
                # Benign: the exact content is already committed from a prior
                # identical persist -- genuinely durable, just not a NEW commit.
                return True, "Git/Archive L5 (already committed, no new changes)"
            return False, f"L5 Git/Archive: git commit failed (exit {commit_proc.returncode}): {(commit_proc.stdout + commit_proc.stderr).strip()[:200]}"
        except FileNotFoundError:
            return False, "L5 Git/Archive: git binary not found -- record written to disk but not committed"
        except subprocess.TimeoutExpired:
            return False, "L5 Git/Archive: git command timed out -- record written to disk but not committed"
    except Exception as e:
        return False, f"L5 Git/Archive error: {e}"

def persist_to_all_layers(task: Dict, evidence: str, summary: str) -> Dict:
    """
    Persist task completion to ALL 5 memory layers.

    Returns dict with results:
    {
        'l1_redis': (success: bool, message: str),
        'l2_postgres': (success: bool, message: str),
        'l3_chromadb': (success: bool, message: str),
        'l4_codegraph': (success: bool, message: str),
        'l5_git': (success: bool, message: str),
        'any_succeeded': bool,
        'durable_succeeded': bool,
        'all_succeeded': bool,
    }

    Task I0000000044 (EG-004, 2026-07-02): completion callers MUST check
    'durable_succeeded', not 'any_succeeded'. L1 (Redis, 24h TTL cache) and L3/L4
    (ChromaDB/CodeGraph, rebuildable indexes) are not durable persistence — a completion
    record that only landed in a 24h cache is not really "remembered." Only L2
    (PostgreSQL) or L5 (git-committed .memory_archive/) count as durable. 'any_succeeded'
    is kept for informational/reporting purposes only (how many of 5 layers responded),
    not as the completion gate.
    """
    results = {
        'l1_redis': persist_to_l1_redis(task),
        'l2_postgres': persist_to_l2_postgres(task, evidence, summary),
        'l3_chromadb': persist_to_l3_chromadb(task, evidence, summary),
        'l4_codegraph': persist_to_l4_codegraph(task),
        'l5_git': persist_to_l5_git(task, evidence, summary),
    }

    # Safely unpack results (handle both tuple and bool returns for robustness)
    def _ok(value) -> bool:
        if isinstance(value, tuple) and len(value) >= 1:
            return bool(value[0])
        return bool(value)

    success_count = sum(1 for value in results.values() if _ok(value))
    durable_succeeded = _ok(results['l2_postgres']) or _ok(results['l5_git'])

    return {
        **results,
        'any_succeeded': success_count > 0,
        'durable_succeeded': durable_succeeded,
        'all_succeeded': success_count == 5,
        'success_count': success_count,
    }
