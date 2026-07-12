# [YOUR-AI-NAME] Operators

Operators are meta-skills that compose 2-4 skills for common complex task patterns.
Instead of manually chaining skills, pick an operator and it sequences everything.

## Available Operators

| Operator | Skills composed | Use when |
|---|---|---|
| `deploy-feature` | worktree-task → build-and-verify → memory-write | shipping any infra or code change |
| `audit-and-fix` | security-review → architecture-review → build-and-verify | pre-release hardening or post-incident review |
| `claim-and-execute` | claim-task → inject_context → [selected-skill] → task-completion-verifier | start of any agent session |

## How operators work

1. Operator `## Brief` tells you which skills to load in sequence
2. Each skill runs to completion before the next starts
3. If any skill fails, operator escalates (Rule 7)
4. Operator completion = all composed skills completed with evidence

## Adding a new operator

Copy one of the operator SKILL.md files. Set `type: operator` in frontmatter.
List composed skills in `## Skills` section. Keep under 150 lines.
