#!/usr/bin/env python3
"""
Memory Aging Pipeline — scans L3 (claude-mem) for stale entries + findings export.

Queries claude-mem for all memories, identifies entries older than
the aging threshold, and outputs a review list. Does NOT delete —
deletion requires human review.

ENHANCED: Now creates findings for stale memories → wiki ingestion

Usage:
  python3 memory_aging.py                # scan with default 180-day threshold
  python3 memory_aging.py --days 90      # custom threshold
  python3 memory_aging.py --json         # output JSON

Task: 0995 (Memory Governance V2)
"""
import sys
import os
import json
import datetime
import argparse
import urllib.request
import urllib.error

# REAL systems for findings export
sys.path.insert(0, '/opt/YOUR-PROJECT/ops/agent')
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

def _read_etc_environment():
    result = {}
    try:
        with open("/etc/environment") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    result[k.strip()] = v.strip()
    except OSError:
        pass
    return result

_etc_env = _read_etc_environment()

def _getenv(key, default=""):
    return os.environ.get(key) or _etc_env.get(key, default)

BASE_URL   = _getenv("CLAUDE_MEM_URL", "http://localhost:37877")
API_KEY    = _getenv("CLAUDE_MEM_API_KEY", "")
PROJECT_ID = _getenv("CLAUDE_MEM_PROJECT", "jeanne-cto")

AGING_THRESHOLD_DAYS = 180

def _headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h

def get_all_memories(limit: int = 200) -> list:
    """Search with broad query to get recent memories."""
    payload = json.dumps({"projectId": PROJECT_ID, "query": "jeanne platform engineering", "limit": limit}).encode()
    req = urllib.request.Request(f"{BASE_URL}/v1/search", data=payload, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())
            return result.get("observations", [])
    except Exception as e:
        print(f"ERROR: cannot fetch memories: {e}", file=sys.stderr)
        return []

def scan(threshold_days: int = AGING_THRESHOLD_DAYS) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=threshold_days)

    memories = get_all_memories()
    if not memories:
        return {"error": "No memories found or claude-mem unreachable", "stale": [], "recent": []}

    stale = []
    recent = []

    for mem in memories:
        created_str = mem.get("createdAt", "")
        mem_id = mem.get("id", "?")
        content = mem.get("content", "")[:120]

        if created_str:
            try:
                created = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_days = (now - created).days
                entry = {"id": mem_id, "age_days": age_days, "created": created_str, "content": content}
                if created < cutoff:
                    stale.append(entry)
                else:
                    recent.append(entry)
            except ValueError:
                recent.append({"id": mem_id, "age_days": -1, "created": created_str, "content": content})
        else:
            recent.append({"id": mem_id, "age_days": -1, "created": "unknown", "content": content})

    return {
        "threshold_days": threshold_days,
        "total": len(memories),
        "stale_count": len(stale),
        "recent_count": len(recent),
        "stale": sorted(stale, key=lambda x: x["age_days"], reverse=True),
        "recent": recent,
    }

def create_findings_for_stale(stale_entries: list) -> int:
    """REAL: Create findings for stale memories → wiki. Returns count created."""
    if not stale_entries:
        return 0

    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()
        created_count = 0

        for entry in stale_entries:
            incident = Incident(
                id=f"incident-stale-mem-{entry.get('id')}-{int(datetime.datetime.now().timestamp())}",
                service="memory-aging",
                incident_type=IncidentType.DATA_QUALITY_ISSUE,
                severity=IncidentSeverity.LOW,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                title=f"Stale memory {entry['age_days']}d old: {entry['id'][:12]}",
                evidence=[{"type": "memory", "text": f"Content: {entry.get('content', '')}"}],
                related_metrics={"age_days": entry['age_days'], "memory_id": entry.get('id')}
            )

            finding = finding_creator.create_finding_from_incident(incident)
            findings_exporter.export_finding(finding)
            created_count += 1

        return created_count
    except Exception as e:
        print(f"  [findings export failed: {e}]", file=sys.stderr)
        return 0

def main():
    parser = argparse.ArgumentParser(description="Memory aging pipeline for L3 claude-mem")
    parser.add_argument("--days", type=int, default=AGING_THRESHOLD_DAYS,
                        help=f"Aging threshold in days (default: {AGING_THRESHOLD_DAYS})")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: CLAUDE_MEM_API_KEY not set — check /etc/environment")
        sys.exit(1)

    result = scan(threshold_days=args.days)

    if args.as_json:
        print(json.dumps(result, indent=2))
        return

    print(f"=== Memory Aging Report ===")
    print(f"Threshold: {result['threshold_days']} days")
    print(f"Total memories scanned: {result.get('total', 0)}")
    print(f"Stale (>{result['threshold_days']}d): {result.get('stale_count', 0)}")
    print(f"Recent: {result.get('recent_count', 0)}")

    if result.get("stale"):
        print("\n--- STALE ENTRIES (review for archival) ---")
        for entry in result["stale"]:
            print(f"  [{entry['id'][:8]}] {entry['age_days']}d old: {entry['content']}")

        # Create findings for stale memories
        print("\nCreating findings for stale memories...")
        findings_created = create_findings_for_stale(result.get("stale", []))
        print(f"  {findings_created} findings exported to wiki")
    else:
        print("\nNo stale entries found.")

    print("\nNOTE: This script outputs only. Deletion requires manual review via claude-mem API.")

if __name__ == "__main__":
    main()
