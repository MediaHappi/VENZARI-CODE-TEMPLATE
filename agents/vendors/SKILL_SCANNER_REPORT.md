# SKILL_SCANNER_REPORT

**Generated:** 2026-05-29 23:56 UTC
**Scanner:** `ops/agent/skill-scanner.sh`
**Action required:** Review candidates below and run `git clone` manually if approved

---

## Known Vendors (already integrated)

- `addyosmani/agent-skills` ✓
- `mattpocock/agent-skills` ✓

---

## Candidate Repositories

| Repo | Stars | Updated | Has SKILL.md | Status |
|---|---|---|---|---|
| [haidrrrry/compose-kotlin-agent-skills](https://github.com/haidrrrry/compose-kotlin-agent-skills) | 24 | 2026-05-27 | Likely | Candidate |
| [scdenney/open-science-skills](https://github.com/scdenney/open-science-skills) | 18 | 2026-05-29 | Likely | Candidate |
| [pamelaaaaa1218/writing-style-skills](https://github.com/pamelaaaaa1218/writing-style-skills) | 2 | 2026-05-28 | Likely | Candidate |
| [HDeibler/universal-design-principles](https://github.com/HDeibler/universal-design-principles) | 1 | 2026-05-20 | Likely | Candidate |
| [lexgabrielp/ai-engineering-toolkit](https://github.com/lexgabrielp/ai-engineering-toolkit) | 0 | 2026-05-28 | Likely | Candidate |
| [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | 56411 | 2026-05-29 | Likely | Candidate |
| [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | 39124 | 2026-05-29 | Likely | Candidate |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 22324 | 2026-05-29 | Likely | Candidate |
| [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) | 20371 | 2026-05-29 | Likely | Candidate |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 13008 | 2026-05-29 | Likely | Candidate |
| [refly-ai/refly](https://github.com/refly-ai/refly) | 7338 | 2026-05-29 | Likely | Candidate |
| [ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) | 5932 | 2026-05-29 | Likely | Candidate |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 5472 | 2026-05-29 | Likely | Candidate |
| [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) | 5209 | 2026-05-29 | Likely | Candidate |
| [zebbern/claude-code-guide](https://github.com/zebbern/claude-code-guide) | 4213 | 2026-05-29 | Likely | Candidate |

---

## How to Evaluate a Candidate

```bash
# 1. Check if repo has SKILL.md files:
curl -s https://api.github.com/search/code?q=SKILL.md+repo:<OWNER>/<REPO> | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_count',0),'SKILL.md files found')"

# 2. Preview skill list:
curl -s https://api.github.com/repos/<OWNER>/<REPO>/git/trees/main?recursive=1 | python3 -c "import sys,json; [print(f['path']) for f in json.load(sys.stdin)['tree'] if 'SKILL' in f['path']]"

# 3. Clone to evaluate:
git clone --depth=1 https://github.com/<OWNER>/<REPO> /tmp/candidate-skills

# 4. If approved, add to vendors:
cp -r /tmp/candidate-skills /opt/YOUR-PROJECT/agents/vendors/<vendor-name>
rm -rf /opt/YOUR-PROJECT/agents/vendors/<vendor-name>/.git
# Then update VENZARI_OVERLAY.md and SKILL_CATALOG.md
```

---

## Next Scan

Run: `bash /opt/YOUR-PROJECT/ops/agent/skill-scanner.sh`
Recommended: Add to Sunday 3am cron alongside `memory-aging.sh`

```bash
# Add to cron (Venzari VPS):
# 0 3 * * 0 bash /opt/YOUR-PROJECT/ops/agent/skill-scanner.sh >> /var/log/skill-scanner.log 2>&1
```
