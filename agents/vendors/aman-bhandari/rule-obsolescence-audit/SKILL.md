---
name: "rule-obsolescence-audit"
description: "Periodically audit Golden Rules and skill constraints to check if they're still needed or can be relaxed. Use quarterly or after major platform changes. Prevents rules from accumulating beyond their useful life. Output: audit report with KEEP/RELAX/RETIRE recommendation for each rule."
version: "1.0"
compatible-roles:
  - platform-engineer
  - reviewer
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash, Read, Write
---

# Skill: Rule Obsolescence Audit

> **Version:** 1.0 | **Adapted from:** aman-bhandari/claude-code-agent-skills-framework

---

## Brief

Audit Golden Rules and skill constraints to check which are still needed.

**When to use:**
- Quarterly (every 3 months)
- After a major platform change (e.g., removing a service that a rule protects)
- After an incident that suggests a rule is preventing a better fix

**Do NOT use when:** You want to bypass a rule you disagree with. This audit is for rules
that have become genuinely obsolete, not rules you find inconvenient.

**Key Facts:**

| Item | Value |
|---|---|
| Rules file | `/opt/YOUR-PROJECT/GOLDEN_RULES.md` |
| Decision log | `/opt/YOUR-PROJECT/docs/architecture/decision-log.md` |
| Output | `docs/audits/rule-obsolescence-YYYY-MM.md` |
| ⛔ FORBIDDEN | Retire a rule that has caused an incident in the past 6 months |

---

## Detail

### Step 1 — List all current rules

```bash
grep "^## RULE" /opt/YOUR-PROJECT/GOLDEN_RULES.md
```

### Step 2 — For each rule, assess

For each rule, answer:
1. **Why was it added?** (check decision-log.md for ADR)
2. **Has the underlying risk changed?** (e.g., service removed, architecture changed)
3. **Has the rule prevented incidents?** (check `.team/inbox/ops.jsonl`)
4. **Is there a better mechanism now?**

### Step 3 — Classify each rule

- **KEEP**: Rule is actively protecting a real risk. Do not change.
- **RELAX**: Rule can be scoped more narrowly. Write updated version.
- **RETIRE**: Underlying risk no longer exists. Write ADR documenting why.

### Step 4 — Write audit report

```bash
mkdir -p /opt/YOUR-PROJECT/docs/audits
# Write to docs/audits/rule-obsolescence-YYYY-MM.md
```

Format:
```markdown
# Rule Obsolescence Audit — YYYY-MM

| Rule | Recommendation | Reason |
|---|---|---|
| Rule 1 | KEEP | Recent incidents prove it still needed |
| Rule 6 | KEEP | liveTurnTimeoutMs still banned — config key still exists |
```

### Step 5 — Commit

```bash
cd /opt/YOUR-PROJECT
git add docs/audits/
git commit -m "audit: rule obsolescence review YYYY-MM"
git push origin main
```

---

## Reference

### Forbidden

Never retire Rule 6 (liveTurnTimeoutMs) or Rule 13 (Claude Code standalone) — both have caused
documented multi-day incidents. These require extraordinary evidence before relaxation.

### Audit cadence

Recommended: quarterly. Trigger: after any major architectural change that removes a service
a rule was written to protect.
