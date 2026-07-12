---
name: "git-branch-cleanup"
description: "Clean stale git worktrees and task branches from YOUR-PROJECT repo. Use after completing task batches or when worktrees accumulate. Lists stale worktrees, removes completed task branches, and prunes remote tracking refs. Prevents worktree/branch accumulation bloat."
version: "1.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash
---

# Skill: Git Branch Cleanup

---

## Brief

Remove stale worktrees and completed task branches from YOUR-PROJECT.

**When to use:**
- After completing a batch of tasks
- When `git worktree list` shows stale entries
- Weekly maintenance

**Do NOT use when:** A task is still in_progress — never remove active worktrees.

---

## Detail

### Step 1 — List all worktrees

```bash
git -C /opt/YOUR-PROJECT worktree list
```

### Step 2 — Remove stale worktrees (no directory exists)

```bash
git -C /opt/YOUR-PROJECT worktree prune
echo "Pruned stale worktrees"
```

### Step 3 — List merged task branches

```bash
# Show branches merged to main (safe to delete)
git -C /opt/YOUR-PROJECT branch --merged main | grep "task/" | head -20
```

### Step 4 — Delete merged task branches

```bash
git -C /opt/YOUR-PROJECT branch --merged main | grep "task/" | xargs -r git -C /opt/YOUR-PROJECT branch -d
echo "Deleted merged task branches"
```

### Step 5 — Prune remote tracking refs

```bash
git -C /opt/YOUR-PROJECT remote prune origin
```

---

## Reference

### Safety check

Only delete branches that are `--merged main`. Never force-delete (`-D`) task branches
without confirming the task is completed in `.tasks/`.
