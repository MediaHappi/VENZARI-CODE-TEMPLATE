---
name: "deploy-feature"
description: "Operator: ship any infrastructure or code change safely. Composes worktree-task → build-and-verify → memory-write in sequence. Use when deploying any change >2 files or any infra change. Ensures SSOT commit, live verification, and memory capture."
version: "1.0"
type: operator
compatible-roles:
  - infrastructure
  - backend
  - devops
composed-skills:
  - worktree-task
  - build-and-verify
  - memory-write
---

## Brief

**Operator: deploy-feature** — sequences the full safe deploy pattern.

When to use:
- Any infra change (Docker, systemd, nginx, SSH)
- Any code change touching >2 files
- Any deployment to production

Do NOT use when: change is docs-only (use worktree-task alone).

## Skills

Run in this order:

### 1. `worktree-task`

Create isolated git worktree. Make changes there. Commit SSOT first (Rule 11).

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load worktree-task
```

### 2. `build-and-verify`

After SSOT commit: deploy to live infrastructure. Verify with curl HTTP status.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load build-and-verify
```

### 3. `memory-write`

After successful deploy: write structured observation to L3 claude-mem.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load memory-write
```

## Failure handling

If step 2 (build-and-verify) fails 3 times → load `escalate` skill (Rule 7).
Do NOT proceed to step 3 if step 2 is failing.

---

## Detail

See `## Skills` section above for the complete step sequence. Each composed skill has its own
`## Detail` section with full commands and verification steps.

---

## Reference

### Failure handling

If any composed skill fails 3 times → load `escalate` skill (Rule 7).
Write failure to `.team/inbox/billy.jsonl` before stopping.

### Doc Impact

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | Update service state if any deploy was made |
