# Protocol: Evidence Contract for Task Completion

**Protocol:** evidence-contract  
**Version:** 1.0  
**Last Updated:** 2026-05-27

---

## Purpose

Every completed task MUST include an `evidence` string proving the work was done and verified. "Should work" is not evidence. "I believe it's fixed" is not evidence.

---

## Evidence Requirements

| Task Type | Required Evidence |
|---|---|
| HTTP service deployed | `curl http://... → HTTP 200 {"status":"ok"}` |
| File created/modified | `git log --oneline -1` showing the commit hash |
| Container started | `docker ps` output showing container name + status |
| Script deployed | Script path + `chmod +x` + test run output |
| Config changed | Before/after diff or the changed line + verification |
| Database migration | Row count before + after, or SELECT result |

---

## Evidence Format

```
<action done> — <verification output>
```

**Examples:**

Good:
```
claude-mem deployed at :37877 — curl http://localhost:37877/healthz → {"status":"ok","runtime":"server-beta"}
```

Good:
```
venzarai-tunnel.service updated with port 37877 — systemctl status venzarai-tunnel → active (running)
```

Good:
```
commit 4cb9139 — 6 shell scripts added to ops/discovery, ops/monitoring, ops/security
```

Bad:
```
"Fixed the issue"
"Should be working now"
"Deployed successfully"
"I think this is correct"
```

---

## Complete Task with Evidence

```bash
# Via bash script
bash /opt/YOUR-PROJECT/ops/agent/complete.sh <task-id> "evidence string here"

# Via Python
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete <task-id> "evidence string"
```

---

## No Evidence = Task Not Complete

If you cannot produce evidence, the task is not complete. Do not mark it done.
Acceptable responses:
- "Task blocked — cannot verify because X"
- "Partial: step 1 verified (evidence), step 2 blocked by Y"
- Escalate to Billy if blocked after 3 attempts

---

## Related

- `ops/agent/complete.sh` — Bash wrapper for task completion
- `ops/agent/task_manager.py` — Python task manager with evidence field
- `agents/protocols/memory-injection.md` — Pre-task memory context injection
