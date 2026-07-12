#!/usr/bin/env python3
"""
Adapter for claude-mem service (:37877 on Venzari VPS, via SSH tunnel on Venzari VPS).
Replaces DEPRECATED: ops/agent/memory_write.py and memory_query.py

claude-mem is a full server-beta stack:
  containers: claude-mem-server, claude-mem-worker, claude-mem-postgres-1, claude-mem-valkey-1
  provider:   LiteLLM at http://172.17.0.1:4001/v1 (jeanne_chat_warm → local Ollama first)
  tunnel:     127.0.0.1:37877 via venzarai-tunnel.service on Venzari VPS

API (v1 — server-beta Postgres runtime):
  GET  /healthz               — no auth required
  GET  /v1/info               — no auth required
  POST /v1/memories           — write a memory {projectId, content}
  POST /v1/search             — search memories {projectId, query, limit}
  POST /v1/context            — get context for a task {projectId, query, limit}

Required env vars (set in /etc/environment on Venzari VPS):
  CLAUDE_MEM_API_KEY   — Bearer token (bound to team jeanne-v5)
  CLAUDE_MEM_PROJECT   — project ID (default: jeanne-cto)

Usage:
  python3 claude_mem_adapter.py health
  python3 claude_mem_adapter.py write "<content>"
  python3 claude_mem_adapter.py query "<search_term>"
  python3 claude_mem_adapter.py context "<task_description>"
"""
import urllib.request, urllib.error, urllib.parse, json, sys, os
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

def _read_etc_environment():
    """Fallback: read /etc/environment for vars not in current shell (cron, sub-processes)."""
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

def _headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h

def _post(path: str, body: dict, timeout: int = 10) -> dict:
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=payload, headers=_headers(), method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}")

def _get(path: str, timeout: int = 5) -> dict:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def health():
    try:
        result = _get("/healthz")
        info = _get("/v1/info")
        print(f"OK: status={result.get('status')} runtime={result.get('runtime')}")
        print(f"OK: authMode={info.get('authMode')} postgres={info.get('postgres',{}).get('initialized')}")
    except Exception as e:
        print(f"ERROR: claude-mem unreachable at {BASE_URL}\n{e}")
        print("  Check: systemctl status venzarai-tunnel.service")
        print("  Check: ssh venzari-vps-billy 'docker ps | grep claude-mem'")
        sys.exit(1)

def detect_contradictions(content: str, task_id: str = "") -> list:
    """Task 1312: Check for contradictions in existing memory on same topic."""
    if not API_KEY:
        return []

    try:
        # Search for similar memories
        result = _post("/v1/search", {
            "projectId": PROJECT_ID,
            "query": content[:100],  # Use first 100 chars as search
            "limit": 5
        })

        observations = result.get("observations", [])
        contradictions = []

        for obs in observations:
            obs_content = obs.get("content", "")
            # Simple heuristic: check if memory contradicts the new content
            # (e.g., "Ollama is slow" vs "Ollama is fast")
            if any(neg in obs_content.lower() for neg in ["not ", "never ", "disabled", "broken"]) and \
               any(pos in content.lower() for pos in ["working", "enabled", "fixed", "fast"]):
                contradictions.append({
                    "id": obs.get("id"),
                    "existing": obs_content[:100],
                    "new": content[:100]
                })

        return contradictions

    except Exception:
        return []

def escalate_contradiction(task_id: str, contradiction: dict):
    """Task 1312: Log contradiction to billy.jsonl for review."""
    from pathlib import Path
    import json as json_module

    inbox = Path("/opt/YOUR-PROJECT/.team/inbox/billy.jsonl")
    inbox.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        "type": "memory_contradiction",
        "task_id": task_id,
        "conflicting_memories": contradiction,
        "action": "Review and reconcile conflicting memories"
    }

    try:
        with open(inbox, 'a') as f:
            f.write(json_module.dumps(entry) + '\n')
    except Exception:
        pass

def write_mem(content: str, task_id: str = "", scope: str = "", branch: str = "",
              author: str = "agent"):
    """Task 1312: Write memory with auto-tagging and contradiction detection.
    Task 1835: Memory governance validation added — rejects writes violating layer protocol."""
    if not API_KEY:
        print("ERROR: CLAUDE_MEM_API_KEY not set in environment")
        sys.exit(1)

    # Task 1835: Governance validation before write
    try:
        from ops.agent.memory_governance_validator import validate_write
        from datetime import datetime, timezone
        metadata = {
            "source_task_id": task_id or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": author,
        }
        result = validate_write(content, destination="claude-mem", metadata=metadata)
        if not result.valid:
            print("⛔ MEMORY GOVERNANCE: write blocked — layer protocol violation", file=sys.stderr)
            for v in result.violations:
                print(f"   [{v.severity}] {v.field}: {v.message}", file=sys.stderr)
            sys.exit(1)
        if result.warnings:
            for w in result.warnings:
                print(f"⚠ MEMORY GOVERNANCE: {w}", file=sys.stderr)
    except ImportError:
        pass  # governance validator optional — never block on import failure

    # Auto-tag with task, branch, and scope
    tagged = content
    if task_id:
        tagged = f"[task:{task_id}] {tagged}"
    if branch:  # Task 1312: auto-tag with branch
        tagged = f"[branch:{branch}] {tagged}"
    if scope:
        tagged = f"[scope:{scope}] {tagged}"

    # Task 1312: Detect contradictions before writing
    contradictions = detect_contradictions(content, task_id)
    if contradictions:
        escalate_contradiction(task_id, contradictions[0])
        print(f"WARNING: Found {len(contradictions)} potential contradiction(s) — escalated to billy.jsonl")

    try:
        result = _post("/v1/memories", {"projectId": PROJECT_ID, "content": tagged})
        mem = result.get("memory", result)
        print(f"OK: memory_id={mem.get('id')} project={mem.get('projectId')}")
    except Exception as e:
        print(f"ERROR: write failed: {e}")
        sys.exit(1)

def query_mem(term: str, limit: int = 10):
    if not API_KEY:
        print("ERROR: CLAUDE_MEM_API_KEY not set in environment")
        sys.exit(1)
    try:
        result = _post("/v1/search", {"projectId": PROJECT_ID, "query": term, "limit": limit})
        observations = result.get("observations", [])
        if not observations:
            print("(no results)")
            return
        for obs in observations:
            print(f"[{obs.get('id','?')[:8]}] {obs.get('content','')}")
    except Exception as e:
        print(f"ERROR: search failed: {e}")
        sys.exit(1)

def context_mem(task: str, limit: int = 5):
    if not API_KEY:
        print("ERROR: CLAUDE_MEM_API_KEY not set in environment")
        sys.exit(1)
    try:
        result = _post("/v1/context", {"projectId": PROJECT_ID, "query": task, "limit": limit})
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"ERROR: context fetch failed: {e}")
        sys.exit(1)

def create_claude_mem_finding(operation: str, success: bool, details: str = ""):
    """REAL: Export claude-mem operations → findings"""
    if not HAS_FINDINGS:
        return
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-claude-mem-{operation}-{int(datetime.now().timestamp())}",
            service="claude-mem-adapter",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL if success else IncidentSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"claude-mem {operation}" if success else f"claude-mem {operation} FAILED",
            evidence=[{"type": "claude_mem_op", "text": f"Operation: {operation}, Success: {success}, Details: {details}"}],
            related_metrics={"operation": operation, "success": success}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


def main():
    if len(sys.argv) < 2:
        print("Usage: claude_mem_adapter.py <health|write|write-scoped|query|context> [args...]")
        print("  health                               — check service is up")
        print("  write <content>                      — store a memory")
        print("  write-scoped <content> <task_id> <scope> — store with scope tags (V2 governance)")
        print("  query <term>                         — search memories")
        print("  context <task>                       — get memory context for a task")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "health":
        health()
    elif cmd == "write" and len(sys.argv) >= 3:
        write_mem(sys.argv[2])
    elif cmd == "write-scoped" and len(sys.argv) >= 5:
        write_mem(sys.argv[2], task_id=sys.argv[3], scope=sys.argv[4])
    elif cmd == "query" and len(sys.argv) >= 3:
        query_mem(sys.argv[2])
    elif cmd == "context" and len(sys.argv) >= 3:
        context_mem(sys.argv[2])
    else:
        print(f"Unknown command '{cmd}' or missing argument")
        sys.exit(1)

if __name__ == "__main__":
    main()
