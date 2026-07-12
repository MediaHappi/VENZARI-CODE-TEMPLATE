#!/usr/bin/env python3
"""
[YOUR-AI-NAME] Phase 5C-4: Memory Recall — Retrieve relevant session memories for agent context

Queries ChromaDB for relevant past experiences based on task keywords/type.
Formats memories as context blocks for injection into agent prompts.

Usage:
  from memory_recall import MemoryRecall
  recall = MemoryRecall()
  context = recall.recall_for_task(task_title="IMPLEMENT: Phase 5C-4...")
  # Returns formatted "Relevant Past Experiences:" section for prompt injection
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any
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

# Configuration - must match session_ingester.py
CHROMADB_URL = os.environ.get("CHROMADB_URL", "http://127.0.0.1:8001")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
TENANT = os.environ.get("CHROMADB_TENANT", "default_tenant")
DATABASE = os.environ.get("CHROMADB_DB", "default_database")
EMBED_MODEL = "nomic-embed-text"
SESSIONS_COLLECTION = "jeanne_sessions"


def create_memory_recall_finding(task_title: str, memories_count: int, success: bool):
    """REAL: Export memory recall event → findings"""
    if not HAS_FINDINGS:
        return
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-mem-recall-{hash(task_title) % 1000000}-{int(datetime.now().timestamp())}",
            service="memory-recall",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Memory recalled: {task_title[:60]}, {memories_count} memories" if success else f"Memory recall failed: {task_title[:60]}",
            evidence=[{"type": "memory_recall", "text": f"Task: {task_title}, Memories: {memories_count}, Success: {success}"}],
            related_metrics={"task": task_title, "memories_count": memories_count, "success": success}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def _get(path: str) -> dict:
    """GET request to ChromaDB."""
    try:
        req = urllib.request.Request(f"{CHROMADB_URL}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"GET request failed: {e}")
        raise


def _post(path: str, body: dict) -> dict:
    """POST request to ChromaDB."""
    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{CHROMADB_URL}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"POST request failed: {e}")
        raise


def _embed(text: str) -> List[float]:
    """Generate embedding via Ollama.

    Task M0000000022: this used to fall back to an SSH tunnel (`ssh venzari-vps-billy`,
    shell=True subprocess) when the direct OLLAMA_URL request failed. Under the current
    single-VPS architecture (GOLDEN_RULES.md: "Venzari VPS eliminated: All services now run
    on single consolidated Venzari VPS", "single VPS, no Tailscale") that SSH alias targets
    the SAME machine this code runs on, reaching the SAME 127.0.0.1:11434 endpoint OLLAMA_URL
    already points at by default -- so the fallback could never provide any additional
    resilience: if the direct request failed, the SSH-wrapped request would fail for the
    identical underlying reason. It also carried real risk with no offsetting benefit
    (shell=True subprocess, hardcoded SSH alias, 30s hang potential). Removed entirely
    rather than gated behind config -- there is no single-VPS scenario where it would ever
    behave differently from the primary attempt.
    """
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
        emb = result.get("embedding")
        if not emb:
            raise RuntimeError("Ollama returned no embedding")
        return emb
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


class MemoryRecall:
    """Retrieve and format relevant session memories for agent context."""

    def __init__(self):
        """Initialize memory recall system."""
        self.collection_id = self._get_collection_id()

    def _get_collection_id(self) -> Optional[str]:
        """Get ChromaDB collection ID for sessions."""
        try:
            result = _get(f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections")
            for coll in result:
                if coll["name"] == SESSIONS_COLLECTION:
                    logger.debug(f"Found sessions collection: {coll['id']}")
                    return coll["id"]
            logger.warning(f"Collection '{SESSIONS_COLLECTION}' not found - memory recall unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to get collection ID: {e}")
            return None

    def recall_for_task(
        self,
        task_title: str,
        task_type: Optional[str] = None,
        n_results: int = 3,
    ) -> str:
        """
        Retrieve and format relevant past experiences for a task.

        Args:
            task_title: The task title/description to find similar experiences for
            task_type: Optional task type (e.g., "IMPLEMENT", "FIX", "MIGRATE")
            n_results: Number of past experiences to retrieve (default 3)

        Returns:
            Formatted string suitable for injection into agent prompt.
            Empty string if no memories found or unavailable.
        """
        if not self.collection_id:
            return ""

        try:
            # Extract keywords from task title
            query_text = task_title
            if task_type:
                query_text = f"{task_type} {task_title}"

            # Limit query length for efficiency
            query_text = query_text[:200]

            logger.debug(f"Recalling memories for: {query_text}")

            # Generate embedding for query
            embedding = _embed(query_text)

            # Query ChromaDB
            result = _post(
                f"/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections/{self.collection_id}/query",
                {
                    "query_embeddings": [embedding],
                    "n_results": n_results,
                    "include": ["documents", "metadatas", "distances"],
                }
            )

            # Extract and format results
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

            if not docs:
                logger.debug(f"No memories found for: {query_text}")
                return ""

            # Format as context block
            context_lines = ["📚 Relevant Past Experiences:"]
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
                task_id = meta.get("task_id", "?") if meta else "?"
                skill = meta.get("skill_used", "") if meta else ""
                relevance = 100 - int(dist * 100)  # Convert distance to relevance %

                context_lines.append(f"\n[{i}] Task {task_id} (relevance: {relevance}%)")
                if skill:
                    context_lines.append(f"    Skill: {skill}")
                # First 150 chars of the experience
                context_lines.append(f"    {doc[:150]}{'...' if len(doc) > 150 else ''}")

            logger.info(f"Recalled {len(docs)} memories for task query")
            result_text = "\n".join(context_lines)
            # Export successful memory recall as finding
            create_memory_recall_finding(task_title, len(docs), True)
            return result_text

        except Exception as e:
            logger.error(f"Memory recall failed: {e}")
            # Export failed memory recall as finding
            create_memory_recall_finding(task_title, 0, False)
            return ""

    def recall_for_phase(self, phase_number: str) -> str:
        """
        Retrieve all experiences from a specific phase (e.g., "Phase 5C-2").

        Args:
            phase_number: Phase identifier (e.g., "5C-2", "5B-3")

        Returns:
            Formatted string with all matching phase experiences.
        """
        return self.recall_for_task(f"Phase {phase_number}", n_results=5)

    def health_check(self) -> bool:
        """Check if memory system is available."""
        return self.collection_id is not None


def format_memory_context(memories: str, max_length: int = 500) -> str:
    """
    Format memory recall output for prompt injection.

    Truncates if needed to stay within token budget.
    """
    if not memories:
        return ""

    lines = memories.split("\n")
    if len(memories) > max_length:
        # Keep header and truncate
        return "\n".join(lines[:3]) + f"\n... ({len(lines)} memories available)"

    return memories


if __name__ == "__main__":
    # CLI for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: memory_recall.py <task_title> [task_type] [n_results]")
        print("Example: memory_recall.py 'Session ingestion' IMPLEMENT 3")
        sys.exit(1)

    task_title = sys.argv[1]
    task_type = sys.argv[2] if len(sys.argv) > 2 else None
    n_results = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    recall = MemoryRecall()
    context = recall.recall_for_task(task_title, task_type, n_results)
    print(context if context else "No memories found")
