# Anthropic Official Skills

**Source:** https://github.com/anthropics/skills  
**Imported:** 2026-05-30  
**Why:** Official canonical SKILL.md format specification. Reference for progressive disclosure template design.

## Key patterns adopted

- YAML frontmatter: `name` (64-char max), `description` (1024-char max)
- Progressive loading: frontmatter first, then instructions
- Minimal required fields: only name + description mandatory

## Skills imported

| Skill | Source | Purpose |
|---|---|---|
| `skill-format-spec` | anthropics/skills | Canonical SKILL.md format reference |
