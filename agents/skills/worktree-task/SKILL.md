---
name: worktree-task
description: |
  Isolated git worktree for non-trivial changes. Use for any change >2 files or any infrastructure change. Creates git worktree, works in isolation, merges back cleanly. Prevents destructive work directly on main.
version: "2.0"
compatible-roles:
  - infrastructure
  - backend
  - devops
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Write, Edit
---

# Skill: Worktree Task — Isolated Git Worktree for Non-Trivial Tasks

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Create an isolated git worktree for tasks estimated > 20 minutes or touching infrastructure, so work-in-progress does not pollute the main branch.

---

### When to Use

- Any task estimated to take > 20 minutes
- Any task touching production infrastructure config (VenzariAI Router, OpenClaw, Nginx, SSH keys)
- Any task requiring multiple commits before the work is complete
- When running `run-task.sh` to get a fully isolated environment

---

---

## Detail

### When NOT to Use

- Simple one-file edits estimated < 10 minutes
- Documentation-only changes
- Read-only investigations (no files to modify)

---

### Process

1. **Use run-task.sh to create the worktree.**
   ```bash
   bash /opt/YOUR-PROJECT/ops/agent/run-task.sh <TASK_ID>
   ```
   This: claims the task, creates a worktree at `.worktrees/<task_id>/`, exports task context as env vars, and prints the working directory.

2. **Confirm the worktree is isolated.**
   ```bash
   git -C /opt/YOUR-PROJECT/.worktrees/<task_id> branch
   ```
   Expected: a branch named after the task ID (e.g., `task/0019-fix-venzarai-router-config`).

3. **Do all work inside the worktree.**
   ```bash
   cd /opt/YOUR-PROJECT/.worktrees/<task_id>
   # Make changes here, not in /opt/YOUR-PROJECT directly
   ```

4. **Commit frequently — at least after each verifiable checkpoint.**
   ```bash
   git add -p  # stage only the relevant changes
   git commit -m "task-<ID>: <what this checkpoint achieves>"
   ```
   Small commits are easier to review and revert.

5. **After completing all DoD items, create a merge commit.**
   ```bash
   cd /opt/YOUR-PROJECT
   git merge --no-ff .worktrees/<task_id>
   git push origin main
   ```
   `--no-ff` preserves the task branch history.

6. **Remove the worktree after merge.**
   ```bash
   git worktree remove /opt/YOUR-PROJECT/.worktrees/<task_id>
   ```

7. **Complete the task with the merge commit hash as evidence.**
   ```bash
   bash /opt/YOUR-PROJECT/ops/agent/complete.sh <TASK_ID> "<summary>" "<git commit hash>"
   ```

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "It's a small change — I'll just edit main directly." | If the change breaks something, rolling back is harder without a branch. Worktrees take 5 seconds to create. |
| "I can't merge because there are conflicts." | Conflicts in worktrees are the same as conflicts in main — but they affect only you, not other agents. Resolve and merge. |
| "I forgot to create a worktree and already edited main." | Create a branch from your current state: `git checkout -b task/<ID>` and continue. Retroactive branching is fine. |
| "The worktree path is confusing." | `run-task.sh` prints the path. Copy it. Use absolute paths for all operations. |

---

### Red Flags

Stop if:
- `git worktree list` shows more than 5 active worktrees — likely stale. Clean up stale ones with `git worktree remove --force`.
- A worktree is on the `main` branch — this defeats the isolation purpose. Delete and recreate on a task branch.
- Merging a worktree creates > 50 line changes in a single commit — the task scope has grown. Split it.

---

### Verification

Worktree task is complete when:

```
# Worktree exists on task branch (show git output)
git worktree list
# Expected: .worktrees/<task_id> on branch task/<task_id>-<slug>

# Merge commit exists (show git log)
git log --oneline -5
# Expected: merge commit "task-<ID>: ..." appears

# Task completed with evidence (show task status)
python3 task_manager.py status <TASK_ID>
# Expected: status=completed, evidence=<commit hash>

# Worktree removed (show git worktree list)
git worktree list
# Expected: .worktrees/<task_id> no longer listed
```

---

## Reference

### Forbidden Actions

| Action | Rule | Why |
|---|---|---|
| Skip SSOT commit | Rule 11 | Infrastructure must be in YOUR-PROJECT first |
| `docker restart` healthy container | Rule 1 | edit→rebuild→verify instead |
| `ANTHROPIC_BASE_URL` system-wide | Rule 13 | Breaks Claude Code OAuth |
| `liveTurnTimeoutMs` in openclaw.json | Rule 6 | Caused 2-day crash loop |

### Doc Impact

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | Update service status if changed |

