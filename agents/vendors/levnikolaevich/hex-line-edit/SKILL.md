---
name: "hex-line-edit"
description: "Hash-verified file editing. Before editing a critical file, record its SHA256 hash. After editing, verify the hash changed as expected. Use when editing high-stakes files where accidental corruption or wrong-version edits would be catastrophic. Catches edit tool failures before they cause incidents."
version: "1.0"
compatible-roles:
  - infrastructure
  - devops
min-claude-version: claude-sonnet-4-6
allowed-tools: Bash, Read, Edit
---

# Skill: Hex-Line Edit (Hash-Verified Editing)

> **Version:** 1.0 | **Adapted from:** levnikolaevich/claude-code-skills

---

## Brief

Hash-verified editing for high-stakes files. Records SHA256 before edit, verifies after.

**When to use:**
- Editing openclaw.json (changes break Telegram if wrong)
- Editing venzarai-router_config.yaml (wrong config breaks all inference)
- Editing systemd service files (wrong config bricks the service)
- Any file where a bad edit causes an immediate production incident

**Do NOT use when:** Editing docs or non-critical files. This adds overhead — use only for
files that if corrupted would cause a production incident.

**Key Facts:**

| Item | Value |
|---|---|
| Hash algorithm | SHA256 (sha256sum) |
| Verification timing | Before AND after edit |
| ⛔ FORBIDDEN | Skip hash check on critical config files |

---

## Detail

### Step 1 — Record pre-edit hash

```bash
FILEPATH="/path/to/critical-file.json"
PRE_HASH=$(sha256sum "$FILEPATH" | cut -d' ' -f1)
echo "Pre-edit hash: $PRE_HASH"
```

### Step 2 — Verify file is what you expect

```bash
# Read the file and confirm you're editing the right version
# This catches stale read tool results
cat "$FILEPATH" | head -5
```

### Step 3 — Make the edit

Use the Edit tool normally. The hash verification catches any tool failures.

### Step 4 — Verify post-edit hash

```bash
POST_HASH=$(sha256sum "$FILEPATH" | cut -d' ' -f1)
echo "Post-edit hash: $POST_HASH"
if [ "$PRE_HASH" == "$POST_HASH" ]; then
  echo "ERROR: File unchanged — edit may have failed"
  exit 1
fi
echo "OK: File changed as expected"
```

### Step 5 — Validate the edited file (format-specific)

```bash
# For JSON files:
python3 -m json.tool "$FILEPATH" > /dev/null && echo "Valid JSON"

# For YAML files:
python3 -c "import yaml; yaml.safe_load(open('$FILEPATH'))" && echo "Valid YAML"
```

---

## Reference

### When hash check fails

If `POST_HASH == PRE_HASH` after an edit:
1. Check if the Edit tool returned an error (it may have silently failed)
2. Re-read the file to see current state
3. Try the edit again
4. If fails 3 times → load `escalate` skill

### Files always requiring hex-line verification

- `/home/billy/.openclaw/openclaw.json` — OpenClaw config (Telegram)
- Venzari VPS `venzarai-router_config.yaml` — VenzariAI Router routing
- Any `/etc/systemd/system/*.service` file
