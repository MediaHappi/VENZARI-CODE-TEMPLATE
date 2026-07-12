---
doc_type: runbook
last_updated: 2026-07-02
---

# Runbook Template

**Formally adopted as the 6th documentation template type (task E0000000010,
`docs/governance/DOC-TEMPLATE-SYSTEM.md`) — a real advisor review found the original 5-type
system missed this genre entirely, despite this repo already having 30+ runbook docs. This
template was already good (validated against real SRE practice — PagerDuty's incident
response docs, the SkeltonThatcher run-book-template — during that review); it needed a name
and a frontmatter tag, not a redesign.**

> Copy this file to `docs/runbooks/<TOPIC>.md` when creating a new runbook.
> Delete all bracketed placeholders. Link this runbook from the relevant LAYER.md.

---

## Problem Statement

[One sentence: what fails, where, and how it manifests to the user or operator.]

---

## Diagnosis (30 seconds)

```bash
# Quick triage — run these first
[command 1]
[command 2]
```

Expected output when healthy:
```
[healthy output sample]
```

---

## Root Causes

| Cause | Probability | Signal |
|-------|-------------|--------|
| [Cause A] | High | [What you see] |
| [Cause B] | Medium | [What you see] |
| [Cause C] | Low | [What you see] |

---

## Resolution Steps

### Cause A — [Name]

```bash
# Step 1
[command]
# Expected: [output]

# Step 2
[command]
# Expected: [output]
```

### Cause B — [Name]

```bash
[command]
```

---

## Rollback

```bash
# How to undo if the fix made things worse
[rollback command]
```

---

## Evidence (how to confirm it's fixed)

```bash
[verification command]
# Expected output confirming resolution:
[expected output]
```

---

## Related

- [Layer runbook](../../01-intelligence/RUNBOOK.md) — [what it covers]
- [Other runbook](./OTHER.md)
- GOLDEN_RULES.md rule [N]
