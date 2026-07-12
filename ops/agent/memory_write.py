#!/usr/bin/env python3
"""
Memory Write Layer — Record findings to L3 semantic memory

Records task completions, advisor findings, and patterns to ChromaDB.
Implements the save path that was missing from the memory system.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))


def record_task_completion(task: Dict, evidence: str, summary: str) -> Optional[str]:
    """
    Record task completion findings to semantic memory (L3).

    Args:
        task: Completed task dict
        evidence: Evidence string (curl output, test results, etc)
        summary: Completion summary

    Returns:
        ID of recorded finding, or None if failed
    """
    try:
        from embedding_pipeline import MemoryLayer
        from embedding_pipeline import embed_text

        memory = MemoryLayer()
        task_id = task.get('id', 'unknown')
        title = task.get('title', 'Unknown task')
        layer = task.get('layer', 'general')

        # Extract key findings from evidence + summary
        finding_text = f"Task: {title}\nSummary: {summary}\nEvidence: {evidence[:500]}"

        # Embed and store
        fact_id = f"task-{task_id}"
        success = memory.embed_and_store(
            fact_id=fact_id,
            content=finding_text,
            domain=layer
        )

        if success:
            print(f"✓ Task {task_id} recorded to memory", file=sys.stderr)
            return fact_id
        else:
            print(f"⚠️  Failed to record task {task_id} to memory", file=sys.stderr)
            return None

    except ImportError:
        print(f"⚠️  Memory layer not available", file=sys.stderr)
        return None
    except Exception as e:
        print(f"⚠️  Error recording to memory: {e}", file=sys.stderr)
        return None


def record_advisor_findings(advisor_id: str, findings: Dict, evidence: str,
                           domain: str = "infrastructure") -> Optional[str]:
    """
    Record advisor findings to semantic memory.

    Args:
        advisor_id: Advisor ID
        findings: Advisor findings dict
        evidence: Evidence/analysis
        domain: Domain/layer

    Returns:
        ID of recorded finding
    """
    try:
        from embedding_pipeline import MemoryLayer

        memory = MemoryLayer()

        # Extract key points from findings
        plan = findings.get('plan', '')
        recommendation = findings.get('recommendation', '')
        finding_text = f"Advisor Analysis:\n{plan}\n\nRecommendation: {recommendation}\n\nEvidence: {evidence[:300]}"

        fact_id = f"advisor-{advisor_id}"
        success = memory.embed_and_store(
            fact_id=fact_id,
            content=finding_text,
            domain=domain
        )

        if success:
            print(f"✓ Advisor {advisor_id} findings recorded to memory", file=sys.stderr)
            return fact_id
        return None

    except Exception as e:
        print(f"⚠️  Error recording advisor findings: {e}", file=sys.stderr)
        return None


def extract_findings_from_evidence(evidence: str) -> Dict:
    """
    Extract key findings from task evidence.
    Look for: errors, patterns, decisions, insights.
    """
    findings = {
        'errors': [],
        'patterns': [],
        'decisions': [],
        'insights': []
    }

    # Simple keyword-based extraction
    lines = evidence.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(err in line_lower for err in ['error', 'failed', 'exception', 'bug']):
            findings['errors'].append(line.strip())
        elif any(pat in line_lower for pat in ['pattern', 'repeated', 'consistent']):
            findings['patterns'].append(line.strip())
        elif any(dec in line_lower for dec in ['decided', 'chose', 'selected', 'implemented']):
            findings['decisions'].append(line.strip())
        elif any(ins in line_lower for ins in ['insight', 'learned', 'discovered', 'found']):
            findings['insights'].append(line.strip())

    return findings


if __name__ == "__main__":
    # Test recording
    test_task = {
        "id": "I0000000001",
        "title": "Test task",
        "layer": "infrastructure"
    }

    result = record_task_completion(
        test_task,
        "curl → HTTP 200; tests passed",
        "Task completed successfully"
    )

    print(f"✓ Test recording: {result}")
