---
name: github-search
description: Search GitHub for existing implementations before building from scratch. Mandatory first step for all BUILD tasks.
triggers:
  - "build"
  - "create"
  - "implement"
  - "write"
  - "scaffold"
  - "before building"
version: "2.0"
---
# github-search Skill

**Invoke this skill before starting any BUILD task.** In most cases, you should copy the code structure rather than build from scratch.

---
## Brief

## When to Use

- Before any BUILD task in any layer
- Before implementing a new script, service, or feature
- Before writing new configuration from scratch

---

## Detail

## Search Protocol

```bash
# 1. Define search terms from the task title
TASK="implement X for Y using Z"
TERMS="X Y Z claude code anthropic"

# 2. Web search
# Search: "github.com TERMS" focusing on:
#   - Repos with 100+ stars (proven solutions)
#   - Recent activity (last 6 months)
#   - Languages: Python, bash, TypeScript ([YOUR-AI-NAME] stack)
#   - Keywords: anthropic, claude, ollama, venzarai-router, openai

# 3. Evaluate each repo
# For each top result:
#   - Does it solve the same problem?
#   - Is the code quality good?
#   - Is the license compatible? (MIT/Apache preferred)
#   - Is the complexity worth importing vs copying?
```

## Decision Matrix

| Situation | Action |
|-----------|--------|
| Repo does exactly what we need, simple | Copy code structure, adapt to [YOUR-AI-NAME] |
| Repo has 1 file we need | Copy that file, add attribution comment |
| Repo is a complete library we'll use heavily | Import as vendor (`agents/vendors/<name>/`) |
| Repo is complex but has key algorithm | Copy the algorithm, rewrite the rest |
| No relevant repos found | Build from scratch, document why |

## Before Importing

**Always run security audit first:**
```bash
git clone --depth=1 https://github.com/<repo> /tmp/candidate
bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh /tmp/candidate
# Only proceed if audit passes (exit 0 or APPROVED WITH WARNINGS)
```

## Import Patterns

### Copy Structure (most common)
```bash
git clone --depth=1 https://github.com/<repo> /tmp/candidate
# Read the key files, understand the approach
# Write your own implementation inspired by it
# Add attribution comment: "# Approach adapted from <repo-url>"
rm -rf /tmp/candidate
```

### Import as Vendor (rare, for complete skill libraries)
```bash
git clone --depth=1 https://github.com/<repo> /tmp/candidate
bash /opt/YOUR-PROJECT/ops/security/github-import-audit.sh /tmp/candidate
cp -r /tmp/candidate /opt/YOUR-PROJECT/agents/vendors/<vendor-name>/
rm -rf /opt/YOUR-PROJECT/agents/vendors/<vendor-name>/.git
# Update SKILL_CATALOG.md and PROJECT_OVERLAY.md
```

## Output Format

When invoking this skill, report:
1. Search terms used
2. Top 3-5 repos found with URLs and star counts
3. Recommended action (copy/import/scratch) with reason
4. Security audit result (if cloned)
5. Attribution if code was copied

---

## Reference

_No reference material defined yet._

