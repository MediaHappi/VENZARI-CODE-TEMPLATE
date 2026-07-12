# [YOUR-AI-NAME] Task Schema — Canonical Definition
**Last updated:** 2026-05-27
**Status:** ACTIVE — all task JSON files must conform to this schema

---

## Section 1: Core Task Fields

Every `.tasks/*.json` file MUST have these fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Zero-padded 4-digit integer, e.g. `"0019"` |
| `title` | string | One-line task description. Becomes the branch name slug. |
| `layer` | string | Which [YOUR-AI-NAME] layer this task belongs to: `00-foundation`, `01-core-agent`, `02-memory`, `03-dashboard`, `04-integrations`, `05-ops`, `unassigned` |
| `description` | string | Detailed task description. May be multi-line. |
| `status` | string | `pending` → `in_progress` → `completed`. Set by `task_manager.py`. |
| `assigned_to` | string\|null | Agent name. Set when claimed. Null when pending. |
| `blocked_by` | array[string] | Task IDs that must be `completed` before this task becomes claimable. Empty array = no dependencies. |
| `created_at` | string | ISO 8601 UTC timestamp. Set at creation. |
| `claimed_at` | string\|null | ISO 8601 UTC timestamp. Set when claimed. |
| `completed_at` | string\|null | ISO 8601 UTC timestamp. Set when completed. |
| `summary` | string\|null | What was done. Set by the completing agent. Required for completion. |
| `evidence` | string\|null | Proof of work: commit hash, curl output, file path. Required for tasks touching infrastructure. |
| `dod` | array[DodItem] | Definition of Done items. See Section 2. |
| `failure_count` | integer | Number of failed attempts. Auto-escalate to Billy when this reaches 3. |
| `requires_review` | boolean | If true, the Reviewer role must approve before task is considered done. Default: false. |

---

## Section 2: DoD Item Schema

Each element of the `dod` array:

```json
{
  "item": "curl -s http://localhost:4001/health returns HTTP 200",
  "verified": false,
  "evidence": ""
}
```

| Field | Type | Description |
|---|---|---|
| `item` | string | A specific, verifiable condition. Must be concrete — not "test it works." |
| `verified` | boolean | Set to `true` by the agent when the item is complete. |
| `evidence` | string | Non-empty proof: command output, commit hash, file path. Prose does not count. |

**`complete.sh` enforces:** all `dod` items must have `verified: true` AND non-empty `evidence` before marking a task complete.

---

## Section 3: Fan-Out / Convergence Schema (from ABSORPTION_STRATEGY.md §5)

For parallel task groups, two optional fields extend the core schema:

| Field | Type | Description |
|---|---|---|
| `group_id` | string\|null | Identifies the parallel group, e.g. `"group-container-audit-001"` |
| `convergence_task` | string\|null | Task ID of the convergence task blocked by this group member |

**Convergence task** is a regular task with:
- `blocked_by: [all group member IDs]`
- `convergence_task: null` (it IS the convergence)
- Its `description` receives `group_result` mailbox messages from all members

### Fan-out/convergence example

Scenario: Audit 5 containers simultaneously, then merge findings.

```json
// Member task (one of five)
{
  "id": "0020",
  "title": "Audit venzarai-router container health",
  "group_id": "group-audit-001",
  "convergence_task": "0025",
  "blocked_by": [],
  "status": "pending"
}

// Convergence task
{
  "id": "0025",
  "title": "Merge container audit findings",
  "group_id": "group-audit-001",
  "convergence_task": null,
  "blocked_by": ["0020", "0021", "0022", "0023", "0024"],
  "status": "pending"
}
```

After each member completes, it sends a `group_result` mailbox message to the convergence task agent:
```bash
python3 /opt/YOUR-PROJECT/ops/agent/mailbox.py send \
  --to=convergence-agent \
  --from=infra-agent \
  --type=group_result \
  --msg='{"task_id": "0020", "outcome": "venzarai-router healthy", "evidence": "HTTP 200 in 0.3s"}'
```

The convergence task becomes claimable automatically once all `blocked_by` tasks are `completed`.

---

## Section 4: Complete Task JSON Example

```json
{
  "id": "0019",
  "title": "Fix venzarai-router warm chain to use Ollama as head",
  "layer": "02-memory",
  "description": "jeanne_primary_warm model group HEAD is incorrectly set to groq/llama-3.3-70b-versatile. Must be ollama_chat/jeanne-primary:latest with timeout:120. This causes all warm-path requests to hit Groq instead of local Ollama.",
  "status": "completed",
  "assigned_to": "infra-agent",
  "blocked_by": [],
  "created_at": "2026-05-27T10:00:00Z",
  "claimed_at": "2026-05-27T10:05:00Z",
  "completed_at": "2026-05-27T11:30:00Z",
  "summary": "Updated venzarai-router_config.yaml: moved jeanne_primary_warm HEAD to ollama_chat/jeanne-primary:latest. VenzariAI Router rebuilt and healthy. Warm path now uses local model.",
  "evidence": "git commit abc1234 + curl http://localhost:4001/health → HTTP 200 + docker ps shows venzarai-router Up (healthy)",
  "requires_review": true,
  "dod": [
    {
      "item": "venzarai-router_config.yaml jeanne_primary_warm HEAD = ollama_chat/jeanne-primary:latest",
      "verified": true,
      "evidence": "git diff abc1234 shows model changed from groq/llama-3.3 to ollama_chat/jeanne-primary"
    },
    {
      "item": "VenzariAI Router container healthy after rebuild",
      "verified": true,
      "evidence": "docker ps: jeannebrain-venzarai-router Up 2 minutes (healthy)"
    },
    {
      "item": "curl http://localhost:4001/health returns HTTP 200",
      "verified": true,
      "evidence": "HTTP 200 in 0.08s"
    }
  ],
  "failure_count": 0,
  "group_id": null,
  "convergence_task": null
}
```

---

## Section 5: File Naming Convention

```
/opt/YOUR-PROJECT/.tasks/<id>-<slug>.json
```

Slug: lowercase alphanumeric + hyphens, max 30 characters, derived from title.
Example: `0019-fix-venzarai-router-warm-chain-to-us.json`

Generated automatically by `task_manager.py create`.
