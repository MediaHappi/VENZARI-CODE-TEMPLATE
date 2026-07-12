---
name: github-reference-extraction
description: Study an open-source reference repository and extract patterns (not code) into YOUR-PROJECT repo-intelligence. Mandatory for all new reference repos before integration.
triggers:
  - "reference repo"
  - "study repo"
  - "extract patterns"
  - "add to registry"
  - "learn from"
version: "1.0"
---
# github-reference-extraction Skill

Extract architectural patterns and inspiration from external open-source repos.
**Never copy code verbatim.** Extract the concept, document the pattern, adapt to [YOUR-AI-NAME]'s architecture.

---

## When to Use

- When a repo is added to `repo-intelligence/reference-repos/REGISTRY.md`
- Before integrating any pattern from an external project
- When Billy says "look at how X does Y" for a reference project

---

## Protocol

### Step 1 — Pre-flight checks

```bash
# 1a. Check license (must be MIT, Apache 2.0, BSD, or similar permissive)
curl -s "https://api.github.com/repos/{owner}/{repo}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('license', {}).get('spdx_id', 'UNKNOWN'))"

# 1b. If you cloned the repo locally, run the import audit
bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh /tmp/{repo-name}
```

**Stop if:** license is GPL, AGPL, SSPL, or unknown. Escalate to Billy.

### Step 2 — Study the repo

Read in this order (web browsing or GitHub CLI):
1. `README.md` — architecture overview, how it works
2. Top-level directory structure — understand module boundaries
3. Key source files relevant to your extraction target (e.g. chat UX → `src/components/Chat*`)
4. Any architecture docs in `docs/` or `ARCHITECTURE.md`

**Limit**: Read ≤ 10 files. If you need more, narrow the extraction target.

### Step 3 — Document findings

Create `repo-intelligence/reference-repos/{repo-name}/analysis.md`:

```markdown
# {Repo Name} — Analysis

**URL:** {url}
**License:** {license}
**Studied:** {date}

## Architecture (1 paragraph)
...

## Key Patterns Identified

| Pattern | Location | Apply to [YOUR-AI-NAME] |
|---------|----------|-----------------|
| Pattern name | `src/path/file.py:line` | What [YOUR-AI-NAME] component |

## What to Adapt

- Specific, actionable: "Use X approach for Y in Z file"
- Not vague: not "improve the UX"

## What NOT to Copy

- Any code under restrictive license sections
- Framework-specific code that ties to their stack
- Code that solves problems we don't have

## Attribution

If any pattern is directly inspired, add to implementing file:
`// Pattern inspired by {repo} ({license}) — {url}`
```

### Step 4 — Update REGISTRY.md

Add or update the entry in `repo-intelligence/reference-repos/REGISTRY.md`:
- Mark `study status` as ✅ STUDIED with date
- Link to `analysis.md`
- Update extraction notes with findings

### Step 5 — Extract to patterns library (if reusable)

If the pattern is general enough to reuse across modules, extract to:
`repo-intelligence/patterns/{category}/{pattern-name}.md`

See pattern categories in REGISTRY.md.

### Step 6 — Commit

```bash
cd /opt/YOUR-PROJECT
git add repo-intelligence/
git commit -m "feat: extract {repo-name} patterns — {1-line summary of what was learned}"
git push origin main
```

---

## Rules

1. **Extract concepts, not code.** Describe what they do and why it works. Write [YOUR-AI-NAME]'s own implementation.
2. **Attribution comments** in any file that uses an inspired pattern (not required for general concepts).
3. **Import audit first** for any file you copy locally — run `github-import-audit.sh`.
4. **Respect license boundaries.** GPL code patterns cannot be integrated even as inspiration in commercial code.
5. **Stay focused.** One extraction target per skill invocation. Don't rabbit-hole.
