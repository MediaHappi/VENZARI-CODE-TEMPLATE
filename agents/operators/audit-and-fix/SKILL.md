---
name: "audit-and-fix"
description: "Operator: pre-release hardening or post-incident review. Composes security-review → architecture-review → build-and-verify. Use before any major deploy, after an incident, or when asked to 'make this production-ready'."
version: "1.0"
type: operator
compatible-roles:
  - security
  - infrastructure
  - reviewer
composed-skills:
  - security-review
  - architecture-review
  - build-and-verify
---

## Brief

**Operator: audit-and-fix** — full hardening pipeline before shipping.

When to use:
- Pre-release security review
- Post-incident review
- "Make this production-ready" requests
- Before any major infrastructure change

Do NOT use when: change is already reviewed and you just need to deploy (use `deploy-feature`).

## Skills

### 1. `security-review`

Scan for exposed secrets, insecure patterns, OWASP issues.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load security-review
```

Fix any HIGH findings before proceeding to step 2.

### 2. `architecture-review`

Check for Golden Rules violations, SSOT drift, role boundary violations.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load architecture-review
```

### 3. `build-and-verify`

Deploy fixed version. Verify with curl. Show HTTP status code.

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py load build-and-verify
```

## Failure handling

Any HIGH security finding → write to `.team/inbox/billy.jsonl` AND fix before deploying.
Three failed verify attempts → load `escalate` skill (Rule 7).

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
