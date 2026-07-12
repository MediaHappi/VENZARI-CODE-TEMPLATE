# Vendor Skill Packs

**Total: 216 skills** across 11 collections — installed by VENZARI CODE Phase 9c.

All vendor skills are MIT or Apache licensed. They are loaded by `ops/agent/skill_loader.py`
and listed in `agents/SKILL_CATALOG.md`.

## Collections

| Collection | Skills | Domain |
|---|---|---|
| `trailofbits-skills/` | 73 | Smart contract + supply chain security |
| `ruflo-skills/` | 38 | AI orchestration, SPARC, swarm |
| `zebbern-security/` | 29 | Ethical hacking, pentest, cloud |
| `mattpocock-skills/` | 28 | TypeScript, productivity, PRDs |
| `agent-skills/` | 23 | General engineering patterns |
| `alirezarezvani/` | 15 | Platform ops, container health |
| `n8n-skills/` | 7 | n8n workflow automation |
| `claude-code-harness/` | — | Claude Code integration docs |
| `anthropics/` | 1 | Official SKILL.md format spec |
| `levnikolaevich/` | 1 | Hash-verified file editing |
| `aman-bhandari/` | 1 | Rule obsolescence audit |

## Usage

```bash
# List all vendor skills
python3 ops/agent/skill_loader.py list vendors

# Load a specific skill
python3 ops/agent/skill_loader.py load mattpocock-skills/engineering/tdd

# Search skills by keyword
python3 ops/agent/skill_loader.py search "security audit"
```

## Adding new vendor packs

1. Create `agents/vendors/<collection-name>/`
2. Add `SKILL.md` files using the template at `agents/skills/SKILL_TEMPLATE.md`
3. Run `python3 ops/agent/scan_skills.py` to rebuild `skill_index.json`
4. Update `agents/SKILL_CATALOG.md`

*Powered by VENZARI CODE — venzari.dev*
