# YOUR-PROJECT Agent Coordination System

The agent coordination system enables multiple Claude AI sessions (and humans) to work on tasks in parallel while maintaining atomicity, avoiding conflicts, and sharing intelligence across the team.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Task Coordination Layer (task_manager.py)                  │
│ - FIFO queue of work (pending → in_progress → completed)  │
│ - Atomic claim/complete via fcntl.LOCK_EX                 │
│ - Fan-out/convergence parallelism (group_id + blocked_by) │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ Task Storage (/.tasks/*.json)                               │
│ Each task is an atomic JSON document with metadata           │
│ - status: pending|in_progress|completed                    │
│ - assigned_to: agent name or null                          │
│ - blocked_by: [list of task IDs that must complete first] │
│ - evidence: commit hash, curl output, file path, etc.      │
└─────────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────┬──────────────────────┬───────────────┐
│ Worktree Isolation   │ Mailbox Messaging    │ 5-Layer Memory│
│ (worktree.py)        │ (mailbox.py)         │ L3 claude-mem │
├──────────────────────┼──────────────────────┼───────────────┤
│ task/<ID> branch     │ .team/inbox/*.jsonl  │ L4 codegraph  │
│ per-task git branch  │ Async agent messages │ L5 git/docs   │
└──────────────────────┴──────────────────────┴───────────────┘
```

## Quick Start for New Sessions

When a Claude session starts and wants to pick up work:

```bash
# 1. Read the CURRENT_STATE.md and GOLDEN_RULES.md
cat /opt/YOUR-PROJECT/system-map/CURRENT_STATE.md
cat /opt/YOUR-PROJECT/GOLDEN_RULES.md

# 2. Claim a task
eval $(bash /opt/YOUR-PROJECT/ops/agent/run-task.sh <YOUR_AGENT_NAME>)

# Now you have:
export TASK_ID TASK_TITLE TASK_LAYER TASK_WORKTREE PROJECT_CTO

# 3. Work in the isolated worktree
cd "$TASK_WORKTREE"

# 4. Make commits to task/<TASK_ID> branch
git add -A
git commit -m "my work for task $TASK_ID"

# 5. Mark complete with evidence
bash /opt/YOUR-PROJECT/ops/agent/complete.sh "$TASK_ID" "Fixed X by doing Y" "commit abc123def"

# 6. Write memory for context preservation (Layer 3 — claude-mem)
CLAUDE_MEM_API_KEY=<your-key> python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py write \
  "Task 0001 fixed X bug in Flask routes. Changed /api/health to return 200 OK. Root cause: ..."
```

## CLI Commands

### Task Manager (task_manager.py)

**List all tasks:**
```bash
python3 task_manager.py list
```
Output: table showing [ID] [STATUS] [ASSIGNED] [TITLE]

**Claim the next available task (atomic, no conflicts):**
```bash
python3 task_manager.py claim <AGENT_NAME>
```
Output: task JSON on success, "No available tasks" if queue empty

**Complete a task with evidence:**
```bash
python3 task_manager.py complete <TASK_ID> "<SUMMARY>" [--evidence TEXT]
```
Examples:
```bash
python3 task_manager.py complete 0001 "Fixed jeanne-heal.sh" --evidence "commit b7fa6aa"
python3 task_manager.py complete 0002 "Cron validated" --evidence "/usr/local/bin/jeanne-heal.sh exists, crontab -l shows entry"
```

**Create a single task:**
```bash
python3 task_manager.py create "<TITLE>" <LAYER> [<DESCRIPTION>] [--dod ITEM1 ITEM2 ...]
```
Example:
```bash
python3 task_manager.py create "Fix login endpoint" backend "Add rate limiting" \
  --dod "endpoint returns 429 on 10 reqs/sec" "logs include client IP"
```

**Check task status:**
```bash
python3 task_manager.py status <TASK_ID>
```

**Create parallel tasks + convergence task (fan-out pattern):**
```bash
python3 task_manager.py create_group <GROUP_ID> <LAYER> <TITLE1> <TITLE2> ... --convergence <CONV_TITLE>
```
Example:
```bash
python3 task_manager.py create_group group-infra backend \
  "Test nginx routes" "Validate certs" "Check cron jobs" \
  --convergence "Deploy infrastructure batch"
```

**Check group status:**
```bash
python3 task_manager.py group_status <GROUP_ID>
```
Shows all member tasks and when convergence task becomes claimable.

### Claim/Complete/List Helpers (Bash)

**Claim next task and print ID + title:**
```bash
bash claim.sh <AGENT_NAME>
# Output: CLAIMED 0001: task title
# Exit code: 0 = success, 1 = no tasks
```

**Complete a task:**
```bash
bash complete.sh <TASK_ID> "<SUMMARY>" [EVIDENCE]
# Calls task_manager.py internally
```

**List tasks (optionally filtered):**
```bash
bash list-tasks.sh          # all tasks
bash list-tasks.sh pending   # pending only
bash list-tasks.sh completed # completed only
```

**Run-task helper (all-in-one):**
```bash
eval $(bash /opt/YOUR-PROJECT/ops/agent/run-task.sh <AGENT_NAME>)
```
This script:
1. Claims next task via claim.sh
2. Creates a git worktree for isolation
3. Exports: TASK_ID, TASK_TITLE, TASK_LAYER, TASK_WORKTREE, PROJECT_CTO
4. Exit code: 0 = success, 1 = no tasks

### Worktree Manager (worktree.py)

Provides isolated git branches per task, so multiple agents can work without conflicts.

**Create a worktree for a task:**
```bash
python3 worktree.py create <TASK_ID>
# Output: Created worktree: /opt/YOUR-PROJECT/.worktrees/0001
#         Branch: task/0001
```
This creates `/opt/YOUR-PROJECT/.worktrees/<TASK_ID>` with a clean branch `task/<TASK_ID>`.

**List active worktrees:**
```bash
python3 worktree.py list
```
Output: git worktree list + summary of .worktrees/ directory

**Complete/merge a worktree:**
```bash
python3 worktree.py complete <TASK_ID>
```
1. Checks for uncommitted staged/modified changes (fails if found)
2. Merges `task/<TASK_ID>` branch back to `main`
3. Removes the worktree

**Abandon a worktree (without merging):**
```bash
python3 worktree.py abandon <TASK_ID>
```

### Mailbox (mailbox.py)

Asynchronous, JSONL-based agent-to-human or agent-to-agent messaging.

**Send a message:**
```bash
python3 mailbox.py send --to=<RECIPIENT> --from=<AGENT_NAME> \
  --type=<MSG_TYPE> --msg="<CONTENT>"
```
Example:
```bash
python3 mailbox.py send --to=billy --from=infrastructure \
  --type=task_complete --msg="Deployed jeanne-heal.sh to all machines"
```

**Read inbox (drain — removes messages):**
```bash
python3 mailbox.py read --inbox=<RECIPIENT>
```

**Peek inbox (read without draining):**
```bash
python3 mailbox.py peek --inbox=<RECIPIENT>
```

### Memory: Write + Query (claude_mem_adapter.py — Layer 3)

**SUPERSEDES:** `memory_write.py` and `memory_query.py` — those scripts no longer exist.
Use `claude_mem_adapter.py` for all semantic memory operations.

Stores engineering observations in claude-mem (HTTP service on Venzari VPS :37877),
backed by PostgreSQL + ChromaDB. Full architecture: `docs/architecture/MEMORY_ARCHITECTURE.md`.

**Write an observation:**
```bash
CLAUDE_MEM_API_KEY=<key> python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py write \
  "VenzariAI Router timeout increased from 25s to 120s. Root cause: warm Ollama chain requires 30-90s."
```

**Query for context:**
```bash
CLAUDE_MEM_API_KEY=<key> python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py context "venzarai-router timeout"
```

**Search observations:**
```bash
CLAUDE_MEM_API_KEY=<key> python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py query "timeout fix"
```

**Health check:**
```bash
python3 /opt/YOUR-PROJECT/ops/agent/claude_mem_adapter.py health
```

**5-layer context injection (all layers at once — use at task claim):**
```bash
CLAUDE_MEM_API_KEY=<key> python3 /opt/YOUR-PROJECT/ops/agent/inject_context.py "<task description>"
```

### Code Intelligence (codegraph_adapter.py — Layer 4)

**SUPERSEDES:** `code_index.py` and `code_query.py` — those scripts no longer exist.
Use `codegraph_adapter.py` for all structural code intelligence.

codegraph is a tree-sitter AST knowledge graph (SQLite, sub-millisecond reads).
Index auto-updates via file watcher. Runs LOCAL on Venzari VPS.

**Verify index is healthy:**
```bash
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py verify
# → OK: codegraph 0.9.6, index 2760 KB
```

**Context for a task (what code is relevant?):**
```bash
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py context "VenzariAI Router routing"
```

**Impact analysis (what would this change break?):**
```bash
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py impact "claim_task"
```

**Search for a symbol:**
```bash
python3 /opt/YOUR-PROJECT/ops/agent/codegraph_adapter.py search "task_manager"
```

Also available as MCP tools: `codegraph_context`, `codegraph_impact`, `codegraph_search`,
`codegraph_callers`, `codegraph_callees`, `codegraph_trace` — use these directly in Claude Code.

### Performance Tools

#### task-poller-improved.py — Event-Driven Task Polling

Replaces the constant `.tasks/` polling loop (every 5s) with zero-polling, event-driven watching. Use instead of a manual polling loop for multi-agent setups.

Three auto-selected modes:
- **inotify** (Linux): kernel FS events, zero latency, zero polling
- **watchdog** (macOS/Windows): FS watcher library, <100ms latency
- **polling** (fallback): smart debouncing if no FS watcher available

Reduces inode thrashing from 2 queries/sec to ~0 with 10+ agents. Scales to 100+ concurrent agents without degradation. See `docs/runbooks/PERFORMANCE_FIXES.md` for full details.

```bash
# Run as standalone poller
python3 ops/agent/task-poller-improved.py

# Import in agent code
from ops.agent.task_poller_improved import TaskPoller

poller = TaskPoller(interval=5, tasks_dir="/opt/YOUR-PROJECT/.tasks")
poller.start()
for task in poller.watch_for_tasks():
    poller.claim_task(task.id, agent_name="my-agent")
    # ... do work ...
    poller.complete_task(task.id)
```

#### context_compact.py — Improved Context Compaction Wrapper

Thin wrapper around `agents/vendors/claude-code-harness/s08_context_compact_improved.py`. Import this instead of the raw s08 module.

Key improvements over the original s08:
- Proactive compaction at 70% token threshold (not 100%)
- Async I/O for large tool results (non-blocking, background thread)
- Subagent compaction every 10 turns (not 30 unbounded turns)
- Corrected token estimation: `len(text) // 4` (Claude's 4:1 char:token ratio)

Falls back automatically to the original `s08_context_compact/code.py` if the improved file is unavailable.

```python
# In agent code — import from here, not from s08 directly
from ops.agent.context_compact import agent_loop, compact_history, reactive_compact, estimate_tokens
```

## Task JSON Schema

Each task is stored as `.tasks/<ID>-<slug>.json`:

```json
{
  "id": "0001",
  "title": "Fix jeanne-heal.sh deployment",
  "layer": "infrastructure",
  "description": "Deploy the health check script and add to crontab",
  "status": "completed",
  "assigned_to": "infrastructure-agent",
  "blocked_by": [],
  "group_id": null,
  "convergence_task": null,
  "created_at": "2026-05-27T10:30:00+00:00",
  "claimed_at": "2026-05-27T10:31:15+00:00",
  "completed_at": "2026-05-27T10:45:00+00:00",
  "summary": "Deployed jeanne-heal.sh to /usr/local/bin, added cron entry",
  "evidence": "commit b7fa6aa, crontab -l verified",
  "dod": [
    {
      "item": "Script executable and in /usr/local/bin",
      "verified": true,
      "evidence": "ls -la /usr/local/bin/jeanne-heal.sh"
    },
    {
      "item": "Cron entry runs every 5 minutes",
      "verified": true,
      "evidence": "crontab -l | grep jeanne-heal"
    }
  ],
  "failure_count": 0
}
```

**Key fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | 4-digit task ID (0001, 0002, etc.) |
| `title` | string | One-line title |
| `layer` | string | domain: backend, frontend, infrastructure, devops, data, security, testing, etc. |
| `description` | string | Detailed requirements |
| `status` | enum | pending \| in_progress \| completed |
| `assigned_to` | string\|null | Agent currently working on it |
| `blocked_by` | array | IDs of tasks that must complete first (e.g., `["0001", "0002"]`) |
| `group_id` | string\|null | For fan-out: all parallel tasks share this ID |
| `convergence_task` | string\|null | For fan-out members: ID of the task that waits for all members |
| `created_at` | ISO8601 | UTC timestamp |
| `claimed_at` | ISO8601\|null | When agent claimed it |
| `completed_at` | ISO8601\|null | When marked done |
| `summary` | string\|null | Agent's completion summary |
| `evidence` | string\|null | Proof of work: commit hash, curl output, file path, test result, etc. |
| `dod` | array | Definition of Done items (each with item, verified, evidence) |
| `failure_count` | int | Number of times agent reported failure (for escalation) |

## Atomicity Guarantee (fcntl.LOCK_EX)

The claim operation uses **file-level locking** to ensure exactly one agent claims a task at a time:

```python
# task_manager.py claim_task()
with open(lock_path, 'w') as lock_file:
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    # ... scan for next task, update JSON, unlock
```

This prevents:
- Two agents claiming the same task
- Race conditions during task list scanning
- Concurrent writes to task JSON files

All writes use atomic temp-file-then-rename:
```python
tmp = str(path) + '.tmp'
with open(tmp, 'w') as f:
    json.dump(task, f, indent=2)
os.rename(tmp, path)  # atomic
```

## Fan-Out / Convergence Pattern (Parallelism)

For work that can be parallelized, use `create_group`:

```bash
python3 task_manager.py create_group group-001 infrastructure \
  "Validate nginx" "Check certs" "Restart services" \
  --convergence "Verify deployment health"
```

This creates:
- Tasks 0010, 0011, 0012: each with `group_id: "group-001"`
- Task 0013: convergence task with `blocked_by: ["0010", "0011", "0012"]`

Each member task has:
```json
{
  "group_id": "group-001",
  "convergence_task": "0013"
}
```

The convergence task starts `pending`. Once all members are `completed`, it becomes claimable automatically (checked during `claim_task`).

**Check group progress:**
```bash
python3 task_manager.py group_status group-001
# Output:
# === Group: group-001 ===
#
#   Members (3):
#   + [0010] Validate nginx
#   + [0011] Check certs
#     [0012] Restart services
#
#   Convergence Task [0013]:
#   Status: READY (all members completed)
```

## Worktree Lifecycle

Each task gets its own isolated git branch:

```bash
eval $(bash run-task.sh my-agent)
# TASK_ID=0001, TASK_WORKTREE=/opt/YOUR-PROJECT/.worktrees/0001

cd "$TASK_WORKTREE"
# You're on branch task/0001, isolated from main

git add file.py
git commit -m "Fix issue X"

# Later: merge back to main
python3 worktree.py complete 0001
# Merges task/0001 → main, removes worktree
```

Benefits:
- No merge conflicts with other agents
- Atomic per-task branches
- Easy rollback: `worktree.py abandon`
- Clean git history: commits stay on task/* branches until merge

## Memory System (5-Layer Architecture)

Full spec: `docs/architecture/MEMORY_ARCHITECTURE.md`  
Agent rules: `agents/protocols/memory-governance.md`

| Layer | Store | Tool | Use for |
|---|---|---|---|
| L1 | Redis | direct redis-cli | Runtime session state |
| L2 | PostgreSQL | psql | System config, structured truth |
| L3 | claude-mem :37877 | `claude_mem_adapter.py` | Engineering observations, semantic search |
| L4 | codegraph (local SQLite) | `codegraph_adapter.py` / MCP tools | Code structure, callers, impact |
| L5 | git + docs/archive/ | git log, decision-log.md | ADRs, institutional decisions |

### Write (L3 — claude-mem)

```bash
CLAUDE_MEM_API_KEY=<key> python3 ops/agent/claude_mem_adapter.py write \
  "Task 0001: Fixed VenzariAI Router timeout. Root cause: warm chain cutoff at 25s, increased to 120s."
```

### Query / Inject Context (L3 + L4 + L5)

```bash
# At task claim — inject all relevant layers at once
CLAUDE_MEM_API_KEY=<key> python3 ops/agent/inject_context.py "<task description>"
```

### Debugging

**Memory/claude-mem unreachable?**
- Check service: `ssh venzari-vps-billy "docker ps | grep claude-mem"`
- Check tunnel: `curl -sf http://localhost:37877/api/health`
- Fallback: proceed without L3 context — inject_context.py skips unavailable layers gracefully

**ChromaDB unreachable?**
- `ssh venzari-vps-billy "docker ps | grep chromadb"`
- ChromaDB is accessed indirectly via claude-mem server — not directly by agents

## Initialization Checklist

When spinning up a new YOUR-PROJECT repo clone:

```bash
# 1. Create task and inbox directories
mkdir -p /opt/YOUR-PROJECT/{.tasks,.team/inbox,.worktrees}

# 2. Initialize git (if new)
cd /opt/YOUR-PROJECT
git init
git remote add origin <repo>

# 3. Pre-index code (optional but recommended)
python3 ops/agent/code_index.py index /opt/YOUR-PROJECT

# 4. Check available tasks
bash ops/agent/list-tasks.sh

# 5. Spawn first agent
eval $(bash ops/agent/run-task.sh my-first-agent)
```

## Debugging

**Task stuck in in_progress?**
```bash
python3 task_manager.py status <TASK_ID>
# Check assigned_to and claimed_at
# If agent is dead, manually reset:
python3 -c "
import json, glob
files = glob.glob('/opt/YOUR-PROJECT/.tasks/<TASK_ID>-*.json')
if files:
    t = json.load(open(files[0]))
    t['status'] = 'pending'
    t['assigned_to'] = None
    json.dump(t, open(files[0], 'w'), indent=2)
"
```

**Worktree merge conflict?**
```bash
cd /opt/YOUR-PROJECT
git merge --abort  # cancel the merge
python3 ops/agent/worktree.py abandon <TASK_ID>  # remove worktree
# Then either:
#   - Fix the conflict manually in a fresh worktree
#   - Create a new task for the conflicting work
```

**Memory/ChromaDB unreachable?**
- Venzari VPS: ensure SSH tunnel to Venzari VPS:8001 is active
- Venzari VPS: ensure ChromaDB container is running
- Both scripts try both localhost:8001 and 127.0.0.1:8001 (tunnel) before failing

## References

- **Task Schema:** § Task JSON Schema (above)
- **Fan-out Pattern:** § Fan-Out / Convergence Pattern
- **Memory Architecture:** § Memory System
- **Atomicity Details:** § Atomicity Guarantee
- **Source Code:** `/opt/YOUR-PROJECT/ops/agent/*.py`
