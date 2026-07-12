---
name: "skill-format-spec"
description: "Reference for the canonical Anthropic SKILL.md format. Use when creating or reviewing skills to ensure proper YAML frontmatter, progressive disclosure structure, and description length. Based on the official anthropics/skills GitHub repository specification."
version: "1.0"
compatible-roles:
  - platform-engineer
  - reviewer
min-claude-version: claude-sonnet-4-6
allowed-tools: Read, Write
---

# Skill: Skill Format Specification (Anthropic Canonical)

> Official Anthropic format reference — use when writing new skills or reviewing existing ones.

---

## Brief

Reference for the official Anthropic SKILL.md format. Use this when:
- Creating a new skill
- Reviewing an existing skill for format compliance
- Running the skill-scanner.sh to validate imports

**Canonical YAML frontmatter fields:**

```yaml
---
name: "skill-name"              # REQUIRED — max 64 chars, kebab-case
description: "..."              # REQUIRED — max 1024 chars
                                # Include BOTH what the skill does AND when to use it
                                # This is what Claude reads to decide relevance
version: "1.0"                  # OPTIONAL — semver recommended
compatible-roles: [list]        # OPTIONAL — which agent roles can use this
min-claude-version: claude-X    # OPTIONAL
allowed-tools: Bash, Read       # OPTIONAL
---
```

**Progressive disclosure structure ([YOUR-AI-NAME] hybrid):**

```
## Brief       ← ~200 tokens — loaded when Claude selects the skill
## Detail      ← ~1000 tokens — loaded when Claude executes the skill  
## Reference   ← ~500 tokens — loaded when Claude needs failure/reference info
```

---

## Detail

### Description writing guide

The `description` field is the most important field. Claude uses it to decide:
1. Whether to auto-suggest this skill for a task
2. Which skill to use when multiple skills could apply

**Good description:** "Use when deploying to Venzari VPS, restarting VenzariAI Router, or any task
touching Docker on 158.220.105.107. Ensures SSOT commit first and verifies with curl."

**Bad description:** "Infrastructure skill for VPS operations."

**Rules:**
- Max 1024 characters
- Mention the system it operates on (VPS, service, port)
- Include trigger phrases ("Use when X", "Use for Y")
- Include the expected outcome

### Skill file structure

```
agents/
  skills/                    ← [YOUR-AI-NAME] native skills
    my-skill/
      SKILL.md               ← required
      references/            ← optional overflow
        detailed-guide.md
  vendors/
    vendor-name/
      skill-name/
        SKILL.md
```

### Validation

```bash
python3 /opt/YOUR-PROJECT/ops/agent/skill_loader.py validate <skill-name>
```

---

## Reference

### Common validation failures

**Missing name or description:** Frontmatter must have both fields.

**Description too long:** Max 1024 characters. Check: `wc -c description-text.txt`

**Skill not discovered:** Must be at correct path depth. SKILL.md at `agents/skills/<name>/SKILL.md`.

### Canonical format source

Official specification: https://github.com/anthropics/skills
