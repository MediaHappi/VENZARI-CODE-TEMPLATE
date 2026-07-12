#!/usr/bin/env python3
"""
[YOUR-AI-NAME] Phase 5C-2: Session Ingester — Store session logs in ChromaDB

Reads sessions.jsonl (from Phase 5C-1 SessionLogger), generates embeddings,
and stores session records in ChromaDB for semantic memory and replay.

Usage:
  python3 session_ingester.py ingest [--batch-size 10]
  python3 session_ingester.py query <term>
  python3 session_ingester.py stats

Environment variables:
  CHROMADB_URL    — ChromaDB endpoint (default: http://127.0.0.1:8001)
  OLLAMA_URL      — Ollama embeddings service (default: http://127.0.0.1:11434)
  SESSIONS_FILE   — Sessions JSONL file (default: .sessions/sessions.jsonl)
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Configuration
CHROMADB_URL = os.environ.get("CHROMADB_URL", "http://127.0.0.1:8001")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
SESSIONS_FILE = Path(os.environ.get("SESSIONS_FILE", ".sessions/sessions.jsonl"))
TENANT = os.environ.get("CHROMADB_TENANT", "default_tenant")
DATABASE = os.environ.get("CHROMADB_DB", "default_database")
EMBED_MODEL = "nomic-embed-text"

# Collections
BASE = f"{CHROMADB_URL}/api/v2/tenants/{TENANT}/databases/{DATABASE}"
SESSIONS_COLLECTION = "jeanne_sessions"  # Collection for session records


def _get(path: str) -> dict:
    """GET request to ChromaDB."""
    req = urllib.request.Request(f"{CHROMADB_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _post(path: str, body: dict) -> dict:
    """POST request to ChromaDB."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{CHROMADB_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _embed(text: str) -> List[float]:
    """Generate embedding via Ollama nomic-embed-text."""
    import subprocess
    import tempfile
    import base64

    try:
        # Try direct URL first
        try:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
            emb = result.get("embedding")
            if not emb:
                raise RuntimeError(f"Ollama returned no embedding: {result}")
            return emb
        except (urllib.error.URLError, urllib.error.HTTPError):
            logger.debug("Direct Ollama URL failed, trying SSH tunnel...")
            # Fallback: use SSH tunnel - base64 encode payload to avoid shell escaping issues
            payload = json.dumps({"model": EMBED_MODEL, "prompt": text})
            payload_b64 = base64.b64encode(payload.encode()).decode()

            cmd = f"ssh venzari-vps-billy 'echo {payload_b64} | base64 -d | curl -s -X POST http://127.0.0.1:11434/api/embeddings -H \"Content-Type: application/json\" -d @-'"
            result_str = subprocess.check_output(cmd, shell=True, timeout=30, text=True)
            result = json.loads(result_str)
            emb = result.get("embedding")
            if not emb:
                raise RuntimeError(f"Ollama returned no embedding: {result}")
            return emb
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


def _get_or_create_collection(name: str) -> str:
    """Get existing collection UUID or create new one."""
    try:
        # List existing collections
        result = _get(f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections")
        for coll in result:
            if coll["name"] == name:
                logger.info(f"Using existing collection: {name} ({coll['id']})")
                return coll["id"]

        # Create new collection if not found
        logger.info(f"Creating collection: {name}")
        result = _post(
            f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections",
            {
                "name": name,
                "metadata": {"hnsw:space": "cosine"},
            }
        )
        collection_id = result.get("id")
        if not collection_id:
            raise RuntimeError(f"Failed to create collection: {result}")
        logger.info(f"Created collection: {name} ({collection_id})")
        return collection_id
    except Exception as e:
        logger.error(f"Failed to get/create collection '{name}': {e}")
        raise


def _extract_key_terms(task_title: str, summary: str) -> str:
    """Extract key terms from task title and summary for better embedding."""
    # Combine and extract significant tokens
    combined = f"{task_title} {summary}"
    # Simple approach: use the combined text (could be enhanced with NLP)
    return combined[:500]  # Cap at 500 chars for efficiency


def _parse_sessions_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Parse line-delimited JSON sessions file."""
    sessions = []
    if not file_path.exists():
        logger.warning(f"Sessions file not found: {file_path}")
        return sessions

    try:
        with open(file_path, "r") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    session = json.loads(line)
                    sessions.append(session)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {line_no}: {e}")
                    continue
        logger.info(f"Parsed {len(sessions)} session records from {file_path}")
        return sessions
    except Exception as e:
        logger.error(f"Failed to read sessions file: {e}")
        raise


def _ingest_sessions(batch_size: int = 10) -> int:
    """Ingest sessions.jsonl into ChromaDB."""
    logger.info(f"Starting session ingestion from {SESSIONS_FILE}")

    # Ensure collection exists
    collection_id = _get_or_create_collection(SESSIONS_COLLECTION)

    # Parse sessions
    sessions = _parse_sessions_jsonl(SESSIONS_FILE)
    if not sessions:
        logger.info("No sessions to ingest")
        return 0

    # Ingest in batches
    total_ingested = 0
    for batch_start in range(0, len(sessions), batch_size):
        batch = sessions[batch_start:batch_start + batch_size]

        # Prepare documents for upsert
        documents = []
        embeddings = []
        metadatas = []
        ids = []

        for session in batch:
            task_id = session.get("task_id", "unknown")
            timestamp = session.get("timestamp", "")
            task_title = session.get("task_title", "")
            summary = session.get("summary", "")
            evidence = session.get("evidence", "")
            skill_used = session.get("skill_used", "")
            status = session.get("status", "unknown")

            # Generate unique ID
            doc_id = f"session-{task_id}-{int(datetime.fromisoformat(timestamp.replace('+00:00', '')).timestamp())}"

            # Create document text (what to embed and search)
            doc_text = _extract_key_terms(task_title, summary)

            # Generate embedding
            try:
                embedding = _embed(doc_text)

                documents.append(f"{task_title}\n{summary}\n{evidence}")
                embeddings.append(embedding)
                metadatas.append({
                    "task_id": task_id,
                    "timestamp": timestamp,
                    "skill_used": skill_used,
                    "status": status,
                    "task_title": task_title[:100],  # Truncate for metadata
                })
                ids.append(doc_id)
                total_ingested += 1
                logger.debug(f"Prepared: {doc_id}")
            except Exception as e:
                logger.warning(f"Failed to embed session {task_id}: {e}")
                continue

        if not documents:
            logger.warning(f"Batch {batch_start//batch_size + 1}: no documents to ingest")
            continue

        # Upsert batch to ChromaDB
        try:
            logger.info(f"Upserting batch {batch_start//batch_size + 1} ({len(documents)} documents)")
            result = _post(
                f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections/{collection_id}/upsert",
                {
                    "ids": ids,
                    "documents": documents,
                    "embeddings": embeddings,
                    "metadatas": metadatas,
                }
            )
            logger.info(f"Batch upserted successfully")
        except Exception as e:
            logger.error(f"Failed to upsert batch: {e}")
            return -1

    logger.info(f"Session ingestion complete: {total_ingested} records stored")
    return total_ingested


def _query_sessions(query_text: str, n_results: int = 5) -> int:
    """Query sessions by semantic search."""
    try:
        # Get collection
        result = _get(f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections")
        collection_id = None
        for coll in result:
            if coll["name"] == SESSIONS_COLLECTION:
                collection_id = coll["id"]
                break

        if not collection_id:
            logger.error(f"Collection '{SESSIONS_COLLECTION}' not found")
            return 1

        # Embed query
        logger.info(f"Embedding query: {query_text[:50]}...")
        embedding = _embed(query_text)

        # Search
        logger.info(f"Searching collection...")
        result = _post(
            f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections/{collection_id}/query",
            {
                "query_embeddings": [embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }
        )

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not docs:
            print(f"No results found for query: {query_text}")
            return 0

        print(f"\n=== Query Results ({len(docs)} hits) ===\n")
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
            print(f"[{i}] distance={dist:.4f}")
            if meta:
                print(f"    Task: {meta.get('task_id')} ({meta.get('status')})")
                print(f"    Skill: {meta.get('skill_used')}")
                print(f"    Time: {meta.get('timestamp')}")
            print(f"    {doc[:200]}{'...' if len(doc) > 200 else ''}")
            print()

        return 0
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return 1


def _stats_sessions() -> int:
    """Print collection statistics."""
    try:
        result = _get(f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections")
        for coll in result:
            if coll["name"] == SESSIONS_COLLECTION:
                collection_id = coll["id"]

                # Count documents
                count = _get(
                    f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections/{collection_id}/count"
                )

                print(f"\n=== Sessions Collection Stats ===")
                print(f"Collection: {coll['name']}")
                print(f"ID: {coll['id']}")
                print(f"Documents: {count}")
                print(f"Dimension: {coll.get('dimension', '?')}d")
                return 0

        print(f"Collection '{SESSIONS_COLLECTION}' not found")
        return 1
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        return 1


def main():
    """CLI entry point."""
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        return 1

    cmd = args[0]

    try:
        if cmd == "ingest":
            batch_size = 10
            if len(args) > 1 and args[1] == "--batch-size" and len(args) > 2:
                batch_size = int(args[2])
            count = _ingest_sessions(batch_size)
            return 0 if count >= 0 else 1

        elif cmd == "query":
            if len(args) < 2:
                print("Usage: session_ingester.py query <term> [n_results]", file=sys.stderr)
                return 1
            query_text = args[1]
            n_results = int(args[2]) if len(args) > 2 else 5
            return _query_sessions(query_text, n_results)

        elif cmd == "stats":
            return _stats_sessions()

        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            print("Commands: ingest, query, stats", file=sys.stderr)
            return 1

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
