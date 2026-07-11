# GOLDEN RULES — [PROJECT NAME]

> These rules apply to every session, every task, every team member.
> Update this file when your environment changes.

---

## Universal Engineering Rules

1. **Never commit secrets** — API keys, passwords, tokens must use `{env:VAR}` syntax or environment variables. The pre-commit hook will block you if you try.

2. **Tests must pass before completing any task** — run tests, record the output as evidence. Never mark a task complete with failing tests.

3. **One task at a time** — claim a task, complete it fully (implement → validate → commit), then claim the next. Do not work on multiple tasks simultaneously.

4. **Record evidence** — every task completion requires at least 3 tool call evidence events. If you can't produce evidence, the task isn't complete.

5. **Use the mode lifecycle** — don't skip modes. discover → plan → implement → validate → review → commit. Each mode has a purpose.

6. **Parameterized queries only** — never build SQL or shell commands via string interpolation with user input.

7. **Backups before migrations** — any database migration requires a backup (or confirmed backup exists) before running.

8. **Meaningful commit messages** — describe what changed and why. "fix stuff" is not a commit message.

9. **Update CURRENT_STATE.md after infrastructure changes** — if you add, remove, or change a service, update `system-map/CURRENT_STATE.md`.

10. **Close the loop** — every session ends with a handoff doc (auto-written by VENZARI CODE). Read the previous handoff at the start of the next session.

---

## Project-Specific Rules

> [FILL IN: Add rules specific to your technology stack, team conventions, and infrastructure below.]
> Examples:
> - "Docker containers must not run as root"
> - "All API endpoints must be authenticated"
> - "Ollama model for code tasks: qwen2.5-coder:7b"

---

*Updated by `venzari-code install` on initial setup. Keep this file current.*
