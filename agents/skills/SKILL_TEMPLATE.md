---
name: skill-name-kebab-case
description: |
  One precise paragraph (max 1024 chars): what problem this skill solves, what system it
  operates on, and the exact outcome when applied correctly. Include trigger phrases for
  auto-selection. Example: "Use when deploying to Venzari VPS, restarting VenzariAI Router, or any
  task touching Docker on 158.220.105.107."
version: "1.0"
compatible-roles:
  - infrastructure
  - backend
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash, Read, Write, Edit
---

# Skill: [Display Name]

> **Version:** 1.0 | **Last verified:** YYYY-MM-DD | **Roles:** [list roles]
> Delete all `[bracketed]` placeholders before committing. All 3 sections are required.

---

## Brief

One paragraph: what problem this solves, what system, expected outcome. Be specific — name
the service, port, file, or process.

**When to use:**
- [Exact trigger phrase 1]
- [Exact trigger phrase 2]
- [Exact trigger phrase 3]

**Do NOT use when:** [Situation where a different skill is better — name the better skill]

**Key Facts:**

| Item | Value |
|---|---|
| Primary VPS | Venzari VPS (127.0.0.1) OR Venzari VPS (158.220.105.107) |
| SSOT config | `/opt/YOUR-PROJECT/[path]` |
| Live path | `/opt/[path]` or `ssh venzari-vps-billy [path]` |
| Health check | `[command]` — Expected: `[output]` |
| ⛔ FORBIDDEN | [Action] — Rule [N] |

**Vision alignment:** [Which [YOUR-AI-NAME]-VISION.md pillar — Memory / Identity / Autonomy / Cost / Interface]

---

## Detail

### Prerequisites

- [ ] [System precondition]
  ```bash
  [verify command]  # Expected: [exact output]
  ```
- [ ] SSOT pulled: `git -C /opt/YOUR-PROJECT pull`

### Step 1 — [Action]

[Why this step is necessary — the constraint or invariant it enforces]

```bash
[full command with no ambiguity]
```

Verify:
```bash
[verification command]
# Expected: [exact output]
```

### Step 2 — [Action]

```bash
[command]
```

### Step 3 — Commit to SSOT (MANDATORY — Rule 11)

```bash
cd /opt/YOUR-PROJECT
git add [specific files — never -A blindly]
git commit -m "$(cat <<'EOF'
[PREFIX]: [What changed]

Skill: [skill-name] | Task: [task-id]
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push origin main
```

### Step 4 — Verify Before Closing (MANDATORY — Rule 2)

```bash
# Show HTTP status — never assume
curl -w "%{http_code}" [affected-endpoint]  # Expected: 200

# No stale docs
bash /usr/local/bin/jeanne-doc-drift-scan "[topic keyword]" --strict
```

---

## Reference

### Common Failures

#### [Most common failure name]

**Symptom:** [What you see]
**Diagnosis:** `[command]`
**Fix:** `[fix command]`

### Forbidden Actions

| Action | Rule | Why |
|---|---|---|
| `docker restart` healthy container | Rule 1 | edit→rebuild→verify instead |
| `ANTHROPIC_BASE_URL` system-wide | Rule 13 | Breaks Claude Code OAuth |
| `liveTurnTimeoutMs` in openclaw.json | Rule 6 | Caused 2-day crash loop |
| [Skill-specific forbidden action] | Rule [N] | [Why] |

### Doc Impact

When this skill runs, update these docs (required before closing task):

| Doc | What to update |
|---|---|
| `system-map/CURRENT_STATE.md` | [Section] |
| `[layer]/RUNBOOK.md` | [Section] |

### Vision Alignment

- [ ] **Memory** — helps [Your-AI-Name] remember across sessions
- [ ] **Identity** — consistent behavior across interfaces
- [ ] **Autonomy** — reduces human intervention
- [ ] **Cost** — keeps operation under $20/month
- [ ] **Interface** — improves human-[Your-AI-Name] interaction

### Quality Checklist

**Critical (fix before committing — blocks skill loading):**
- [ ] Frontmatter: name (64-char max), description (1024-char max), version, compatible-roles
- [ ] No broken file paths
- [ ] All commands tested live

**Major (fix — degrades effectiveness):**
- [ ] Brief: trigger phrases specific enough for auto-selection
- [ ] Brief: "Do NOT use when" names a better skill
- [ ] Brief: Key Facts table complete with health check command
- [ ] Detail: Step 3 SSOT commit present
- [ ] Detail: Step 4 verify with curl (shows HTTP status, never "should work")
- [ ] Reference: Forbidden Actions table filled in (at minimum 3 rows)
- [ ] Reference: Doc Impact table complete
- [ ] Under 400 lines total (use references/ subdirectory for overflow)

**Minor (evaluate):**
- [ ] Imperative voice ("Run X", not "You should run X")
- [ ] Vision alignment checked
- [ ] Common Failures has at least one real case
