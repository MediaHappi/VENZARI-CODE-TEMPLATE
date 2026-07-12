---
name: security-review
description: |
  Scan for exposed secrets, insecure patterns, and OWASP issues. Use before any major deploy or when asked to audit security. Checks for hardcoded credentials, insecure configs, and Golden Rules violations.
version: "2.0"
compatible-roles:
  - security
  - infrastructure
  - reviewer
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Security Review — Secrets, Keys, Permissions

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Audit the [YOUR-AI-NAME] codebase and VPS configuration for exposed secrets, wrong SSH keys, and file permission drift — before any deployment or after any config change.

---

### When to Use

- Before pushing any commit that touched config files, `.env`, or key material
- After any new agent or script is added to `/opt/YOUR-PROJECT/ops/`
- When a new SSH key or API key is added to the system
- As part of the quarterly security sweep task
- Whenever `git log` shows a config file was modified in the last 24 hours

---

---

## Detail

### Process

1. **Scan git history for secrets.**
   ```bash
   cd /opt/YOUR-PROJECT
   git log --all -S "sk-" -- . | head -20
   git log --all -S "GROQ_API_KEY" -- . | head -10
   git log --all -S "-----BEGIN" -- . | head -10
   git log --all -S "password" --name-only -- . | head -20
   ```
   If any of these return commits, inspect each one:
   `git show <hash> -- <file>` — is the secret still present? Was it ever committed?

2. **Scan working tree for untracked secrets.**
   ```bash
   grep -r "sk-" /opt/YOUR-PROJECT --include="*.json" --include="*.yaml" --include="*.env" -l 2>/dev/null
   grep -r "GROQ_API_KEY\s*=" /opt/YOUR-PROJECT --include="*.py" --include="*.sh" -l 2>/dev/null
   find /opt/YOUR-PROJECT -name "*.pem" -o -name "*.key" -o -name "id_rsa" 2>/dev/null
   ```
   All actual secrets must live in `.env` files that are in `.gitignore`. Never in committed code.

3. **Verify .gitignore covers sensitive files.**
   ```bash
   cat /opt/YOUR-PROJECT/.gitignore | grep -E "\.env|\.key|\.pem|secret"
   ```
   If `.env` is not in `.gitignore`, add it immediately before doing anything else.

4. **Verify SSH key correctness for Venzari VPS.**
   ```bash
   # Check which key is used by the venzari-vps-billy alias
   grep -A5 "venzari-vps-billy" ~/.ssh/config
   ```
   Expected: `IdentityFile ~/.ssh/id_ed25519_brain_mesh`
   BANNED: `id_rsa` for billy@ on Venzari VPS — this is the wrong key (auth failure).

5. **Check file permissions on sensitive paths.**
   ```bash
   stat -c "%a %n" /opt/YOUR-PROJECT/ops/agent/*.sh
   stat -c "%a %n" ~/.ssh/id_ed25519_brain_mesh 2>/dev/null || true
   ls -la /opt/YOUR-PROJECT/.tasks/
   ls -la /opt/YOUR-PROJECT/.team/inbox/
   ```
   SSH private keys must be `600`. Scripts must be `755` or `644`. Task JSON must not be world-writable.

6. **Check for exposed ports.**
   ```bash
   ss -tlnp | grep -v "127.0.0.1"
   ```
   No [YOUR-AI-NAME] service should bind to `0.0.0.0` except explicitly intended public services. ChromaDB, PostgreSQL, Redis must be bound to `127.0.0.1`.

7. **Check cron for injected commands.**
   ```bash
   crontab -l 2>/dev/null
   cat /etc/cron.d/* 2>/dev/null | grep -v "^#"
   ```
   Any cron entry not in the CONTEXT.md known-crons list is suspicious.

8. **Document findings.**
   List: secrets found (yes/no), SSH key correct (yes/no), permissions clean (yes/no), no unexpected open ports (yes/no).

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "I didn't commit any secrets." | Git history is permanent. Verify with `git log -S`. What you think you didn't commit may have slipped in. |
| "The `.env` file is gitignored so it's fine." | Verify the `.gitignore` entry exists. "It should be gitignored" is not the same as "it is gitignored." |
| "id_rsa works fine for root@Venzari VPS." | `id_rsa` is for root@, NOT billy@. Using the wrong key for billy@ causes auth failures that cascade to agent crashes. |
| "Permissions look fine visually." | Show `stat` output. Visual inspection misses setuid bits and group-write permissions. |
| "No one has access to this VPS so it doesn't matter." | Defense in depth. A secret in git is a secret in logs, backups, and CI runners — forever. |
| "It's just a test key." | Test keys get rotated into prod by accident. Treat all keys as prod. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- `git log -S "sk-"` returns any results — a live API key was committed. Rotate the key first, then clean history.
- `id_rsa` is found configured as the IdentityFile for billy@ on Venzari VPS — fix SSH config immediately.
- ChromaDB, PostgreSQL, or Redis is bound to `0.0.0.0` — these must NEVER be publicly accessible.
- Any `.env` file appears in `git status` as staged or tracked — unstage and add to `.gitignore` immediately.
- SSH private key file permissions are not `600` — fix immediately with `chmod 600`.
- An unknown cron entry is running a script not in the YOUR-PROJECT repo.

---

### Verification

Security review is complete when all of the following are documented:

```
# Git history clean (show command + output or "no results")
git log --all -S "sk-" -- . | head -5
# Expected: no output

# .gitignore covers .env (show grep output)
grep "\.env" /opt/YOUR-PROJECT/.gitignore
# Expected: .env or *.env present

# SSH key correct (show config lines)
grep -A5 "venzari-vps-billy" ~/.ssh/config | grep IdentityFile
# Expected: id_ed25519_brain_mesh

# Permissions clean (show stat output)
stat -c "%a %n" ~/.ssh/id_ed25519_brain_mesh
# Expected: 600

# No public bindings on sensitive services (show ss output)
ss -tlnp | grep -E "5432|8001|6379"
# Expected: all bound to 127.0.0.1 only
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

