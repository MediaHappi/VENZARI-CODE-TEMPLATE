---
name: task-completion-verifier
description: |
  BLOCKING GATE: Must run before every python3 task_manager.py complete call.
  Verifies task is GENUINELY complete by checking DoD items live, running doc-drift
  scanner to find stale docs, and confirming SSOT is pushed. Prevents paper-completions.
  Triggers on: "mark task done", "complete the task", "task_manager.py complete".
version: "2.0"
compatible-roles:
  - infrastructure
  - backend
  - frontend
  - devops
  - security
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---
# Skill: Task Completion Verifier

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Roles:** all roles
> This skill is NON-OPTIONAL. Every task closes through this gate. No exceptions.

---

---
## Brief

## Overview

Prevents the worst habit in autonomous engineering: marking tasks done when the work is only
partially complete. Three failure modes this blocks:

1. **Artifact not deployed** — script committed to SSOT but never copied to /usr/local/bin
2. **Docs not updated** — CURRENT_STATE.md still shows old state, RUNBOOK still has wrong commands
3. **VPS state != claimed** — "verified: HTTP 200" written without actually running curl

**Vision alignment:** Autonomy — a system that marks fake completions cannot be trusted to operate unsupervised.

---

## When to Use

- Before EVERY `python3 ops/agent/task_manager.py complete` call
- When reviewing whether a task was genuinely completed (audit tasks)
- When another agent's task summary says "completed" but the system behaviour doesn't match

**Do NOT use when:** The task has not been attempted yet. This is a close-gate, not a start-gate.

---

## Vision Alignment

- [x] **Autonomy** — A system that self-reports false completions cannot self-repair. This skill makes autonomous operation trustworthy.
- [x] **Identity** — Consistent, honest reporting of system state is core to [Your-AI-Name]'s identity.

---

## Detail

## The Blocking Gate — Do Not Pass Without Running This

```
┌─────────────────────────────────────────────────────┐
│  BEFORE task_manager.py complete — RUN ALL 4 GATES  │
│                                                     │
│  Gate 1: DoD items verified live                    │
│  Gate 2: Artifacts deployed (not just committed)    │
│  Gate 3: Docs updated (doc-drift scan passes)       │
│  Gate 4: SSOT committed and pushed                  │
│                                                     │
│  ALL 4 MUST PASS. Any failure = do not close.       │
└─────────────────────────────────────────────────────┘
```

---

## Process

### Gate 1 — Parse and Verify Each DoD Item Live

```bash
TASK_ID="0XXX"  # replace with actual task ID
TASK_FILE=$(ls /opt/YOUR-PROJECT/.tasks/${TASK_ID}-*.json 2>/dev/null | head -1)

python3 -c "
import json
d = json.load(open('$TASK_FILE'))
print('=== Task:', d['title'])
print('DoD items:')
for i, item in enumerate(d.get('dod', []), 1):
    print(f'  {i}. {item}')
"
```

For each DoD item, run the actual verification command. Examples:

| DoD says | Verify with |
|---|---|
| "deployed to /usr/local/bin" | `ls -la /usr/local/bin/<script>` |
| "HTTP 200" | `curl -sf <url> -w " HTTP:%{http_code}"` |
| "service active" | `systemctl is-active <service>` |
| "committed to SSOT" | `git -C /opt/YOUR-PROJECT log --oneline -1` |
| "Venzari VPS deployed" | `"ls -la /usr/local/bin/<script>"` |
| "doc updated" | `grep "Last updated.*2026-05-30" <doc-path>` |

**BLOCKING:** Any DoD item you cannot verify with a real command = task is NOT complete. Do the work, then close.

---

### Gate 2 — Check Artifacts Are Deployed, Not Just Committed

The most common failure: file exists in SSOT but was never `cp`'d to live system.

```bash
# For every script mentioned in the task, check BOTH locations:

# 1. In SSOT (committed):
ls /opt/YOUR-PROJECT/ops/venzari-vps/scripts/<script>

# 2. On live system (deployed):
ls /usr/local/bin/<script>
# or for Venzari VPS:
"ls /usr/local/bin/<script>"

# Config files — check SSOT vs live:
diff /opt/YOUR-PROJECT/ops/configs/venzari-vps/venzarai-router_config.yaml \
     <("cat /opt/venzarai-router/venzarai-router_config.yaml") 2>/dev/null | head -20
# Expected: no diff (or only expected differences)
```

**BLOCKING:** If script is in SSOT but not deployed — deploy it before closing.

---

### Gate 3 — Doc-Drift Scan (BLOCKING — Rule 14)

Every task that changes a system or process MUST update all docs referencing that topic.

```bash
# Run the scanner — use keywords from the task title
bash /usr/local/bin/jeanne-doc-drift-scan "<task-keyword>" --strict
# Exit 0 = all docs current. Exit 1 = STALE DOCS FOUND — update them first.
```

**Which docs to update** (by task type):

| Task type | Docs that MUST be updated |
|---|---|
| New script deployed | `system-map/CURRENT_STATE.md`, `system-map/SERVICES_INVENTORY.md`, relevant `RUNBOOK.md` |
| Service config changed | `CURRENT_STATE.md`, relevant `RUNBOOK.md`, `docs/architecture/` if routing changed |
| VenzariAI Router config changed | `01-intelligence/RUNBOOK.md`, `CURRENT_STATE.md`, `CONTEXT.md` |
| CLAUDE.md changed | Both VPS deployed, template updated |
| New ADR | `docs/architecture/decision-log.md` updated, `CURRENT_STATE.md` ADR count |
| Skill added/changed | `agents/SKILL_CATALOG.md`, `agents/INDEX.md`, skill count in CURRENT_STATE |
| Golden Rule added | `GOLDEN_RULES.md`, `CLAUDE.md` (both VPS), `ops/templates/CLAUDE.md` |

**BLOCKING:** Re-run scanner after updating docs. Must exit 0 before closing.

---

### Gate 4 — SSOT Committed and Pushed

```bash
# Check nothing unstaged
git -C /opt/YOUR-PROJECT status --short | head -10
# Expected: empty (or only task .json files)

# Check pushed to GitHub
git -C /opt/YOUR-PROJECT log --oneline origin/main..main | head -5
# Expected: empty (local == remote) OR the commits you just made show here

# Push if needed
git -C /opt/YOUR-PROJECT push origin main
```

**BLOCKING:** Unpushed commits = task is not in SSOT = cannot close.

---

### Final — Call complete with --verify

```bash
python3 /opt/YOUR-PROJECT/ops/agent/task_manager.py complete \
  "$TASK_ID" \
  "[One-sentence summary of what was done and what evidence proves it]" \
  --evidence "[Specific command and output that proves completion, e.g., 'curl :4001 → HTTP:200']" \
  --verify
```

The `--verify` flag requires `--evidence` to be set. If you cannot write specific evidence, you have not verified the task.

---

## trailofbits Issue Categorization for Failed Gates

When a gate fails, categorize the failure before deciding how to proceed:

### Critical failure (fix immediately, do not skip)
- DoD item is false — the claimed work was never done
- Artifact deployed to SSOT but not to live VPS
- CURRENT_STATE.md still shows old state

### Major failure (fix before closing)
- Docs are stale (doc-drift scanner fails)
- Summary describes work not actually done
- Evidence is "it should work" instead of a real command output

### Minor failure (fix and note)
- Doc date updated but content not fully refreshed
- Evidence command works but output slightly different from expected

**Three-strike rule (GOLDEN_RULES.md Rule 7):** If you fix a gate failure and it fails again three times, STOP. Write to `.team/inbox/billy.jsonl` and escalate. Do not loop.

---

---

## Reference

## Forbidden Actions

| Action | Why forbidden |
|---|---|
| Marking complete without running doc-drift scan | Violates Rule 14 — leaves docs stale |
| Writing "it should work" as evidence | Rule 2 — verify with curl/command, not assumptions |
| Closing without pushing to SSOT | Rule 11 — SSOT first |
| Skipping this skill because "it's a small task" | No exceptions — paper-completions compound |

---

## Doc Impact

This skill itself does not change docs. But it ENFORCES that the task being closed has updated:
- `system-map/CURRENT_STATE.md`
- Any `RUNBOOK.md` for the affected layer
- Any architecture docs if routing or structure changed

---

