---
name: deploy-script
description: |
  Deploy and manage operational scripts to /usr/local/bin/ on Venzari VPS or Venzari VPS. Use when adding or updating system scripts. Commits to SSOT first, then deploys. Verifies execution.
version: "2.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read, Write
---

# Skill: Script Deployment

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Deploy or update a script to /usr/local/bin/ (or any system path) safely by reading from the repo, diffing against the live version, backing up, deploying, testing, and confirming cron registration if required.

---

### When to Use

- Deploying a new operational script (health check, heal, backup, sync)
- Updating an existing script in /usr/local/bin/
- Adding or modifying a cron entry for any operational script
- Any task description that includes the words "deploy script", "update script", or "install script"

---

---

## Detail

### Process

1. **Read the source from the repo — do not edit the live file directly.**
   Source of truth is always `/opt/YOUR-PROJECT/ops/` or the relevant layer directory.
   ```bash
   cat /opt/YOUR-PROJECT/ops/<path>/<script>.sh
   ```

2. **Read the live version (if one exists).**
   ```bash
   cat /usr/local/bin/<script>.sh 2>/dev/null || echo "NO_LIVE_VERSION"
   ```
   If no live version, skip to step 4.

3. **Diff repo version against live version.**
   ```bash
   diff /opt/YOUR-PROJECT/ops/<path>/<script>.sh /usr/local/bin/<script>.sh
   ```
   Review every difference. Understand each one before proceeding.
   If the diff shows changes you did not intend, stop and investigate before deploying.

4. **Syntax-check the source script.**
   ```bash
   bash -n /opt/YOUR-PROJECT/ops/<path>/<script>.sh
   ```
   If this exits non-zero, fix the syntax error in the repo. Do not deploy a broken script.

5. **Backup the live version.**
   ```bash
   cp /usr/local/bin/<script>.sh /usr/local/bin/<script>.sh.bak.$(date +%Y%m%d-%H%M%S)
   ```
   Skip this step only if there is no live version (step 2 returned NO_LIVE_VERSION).

6. **Deploy from repo to live.**
   ```bash
   cp /opt/YOUR-PROJECT/ops/<path>/<script>.sh /usr/local/bin/<script>.sh
   chmod +x /usr/local/bin/<script>.sh
   ```

7. **Run a dry-run or safe test.**
   If the script supports `--dry-run`:
   ```bash
   /usr/local/bin/<script>.sh --dry-run 2>&1
   echo "Exit code: $?"
   ```
   The dry-run must exit 0. If it exits non-zero, revert to the backup immediately (step 8) and investigate.

   If no `--dry-run` flag: run with a non-destructive argument (e.g., `--status`, `--check`) or read the script to confirm the first operation is safe to run.

8. **Revert procedure (if dry-run fails).**
   ```bash
   cp /usr/local/bin/<script>.sh.bak.<timestamp> /usr/local/bin/<script>.sh
   chmod +x /usr/local/bin/<script>.sh
   ```

9. **Add or confirm cron entry (if the script is scheduled).**
   Check for existing entries first:
   ```bash
   crontab -l | grep <script_name>
   ```
   If an entry already exists: confirm it matches the intended schedule. Do not add a duplicate.
   If no entry exists and a schedule is required:
   ```bash
   (crontab -l 2>/dev/null; echo "<schedule> /usr/local/bin/<script>.sh >> /var/log/<script>.log 2>&1") | crontab -
   ```
   Confirm the addition:
   ```bash
   crontab -l | grep <script_name>
   ```
   Expected: exactly one entry.

10. **Confirm the deployed script matches the repo version.**
    ```bash
    diff /opt/YOUR-PROJECT/ops/<path>/<script>.sh /usr/local/bin/<script>.sh
    ```
    Expected: no output (files are identical).

---

### Rationalizations

| Excuse | Rebuttal |
|---|---|
| "The repo version is fine — I don't need to diff." | "Fine" is not a diff. Diffs take 3 seconds. An unreviewed change can overwrite a live fix that never made it back to the repo. Always diff. |
| "I'll skip the dry-run — it's the same script as before." | Scripts accumulate environment-dependent bugs. The dry-run catches permission errors, missing dependencies, and path issues before they cause an outage. Run it. |
| "I'll edit the live file directly — it's faster." | Editing live bypasses version control. The next deploy from repo will silently overwrite your change. Always edit in the repo and deploy from there. |
| "The backup isn't necessary for a small change." | "Small change" is a rationalization, not a risk assessment. Backups take 2 seconds. Restoring from an absent backup takes hours. Always back up. |
| "I already added this cron entry — it must be there." | "Must be" is not `crontab -l`. Run the check. Duplicate crons caused the 2026-05-27 Telegram outage (root cause #3). |
| "The script modifies some files outside its scope — that's fine for this purpose." | This is a Red Flag. Stop and escalate. Scripts that touch files outside their declared scope are a safety boundary violation. |

---

### Red Flags

Stop immediately and escalate to Billy if:

- `bash -n <script>.sh` exits non-zero — the script has a syntax error. Do not deploy.
- Dry-run exits non-zero — something in the environment is wrong. Do not deploy.
- The script contains `rm -rf` without a specific, bounded path — it must not use wildcards on system directories.
- The script modifies files outside its declared operational scope (e.g., a heal script that edits VenzariAI Router config).
- Diffing reveals changes you did not make and cannot explain — investigate before deploying.
- `crontab -l` shows the script entry more than once — remove all duplicates before proceeding.

---

### Verification

Deployment is complete when ALL of the following are confirmed:

```bash
# 1. Syntax check passes
bash -n /usr/local/bin/<script>.sh
echo "Exit code: $?"
# Expected: Exit code: 0

# 2. Dry-run exits cleanly
/usr/local/bin/<script>.sh --dry-run 2>&1
echo "Exit code: $?"
# Expected: Exit code: 0

# 3. Deployed file matches repo source
diff /opt/YOUR-PROJECT/ops/<path>/<script>.sh /usr/local/bin/<script>.sh
# Expected: no output

# 4. Cron entry confirmed (if scheduled)
crontab -l | grep <script_name>
# Expected: exactly one line matching the intended schedule
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

