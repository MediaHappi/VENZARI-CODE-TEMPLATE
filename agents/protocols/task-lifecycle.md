# Protocol: Task Lifecycle

**Protocol:** task-lifecycle
**Version:** 1.0
**Last Updated:** 2026-07-02

---

## Purpose

Define the exact claim → execute → verify → complete → recover lifecycle every task follows,
so agents don't improvise the ordering and skip a step that matters (a worktree, a typed gate,
a memory write).

---

## The Lifecycle

| Step | Command | Notes |
|---|---|---|
| 1. Claim | `python3 ops/agent/task_manager.py claim <role> --task <id>` | **Verify `status` is actually `in_progress` after claiming** — silent-block gates (REPRODUCIBILITY, DESIGN_REVIEW, ACCEPTANCE) can leave a task looking claimable in the preview message while the real claim didn't take. |
| 2. Worktree | `git worktree add .worktrees/<id> -b task/<id>` | Required for anything touching >2 files or infrastructure (Rule 9). `TASKS_DIR` in `task_manager.py` is a hardcoded absolute path — task read/write always lands in the main repo's `.tasks/`, not the worktree's, even while claimed work happens in the worktree. |
| 3. Implement | — | Do the real work. Prefer fixing root causes over patching symptoms. |
| 4. Verify | `python3 -m pytest ops/tests/ -q` + task-specific checks | Run the full suite, not just the files you touched — cross-file regressions are real. |
| 5. Commit | `git add ... && git commit` (worktree), then `git merge task/<id> --no-ff` (main repo), `git push` | SSOT first, per Rule 11 — commit before applying to any live infrastructure. |
| 6. Complete | `python3 ops/agent/task_manager.py complete <id> "summary" --evidence "..." --skill <skill>` | `--skill` is mandatory (P1-4). Evidence must be real command output, not a description. |
| 7. Clean up | `git worktree remove .worktrees/<id> && git branch -d task/<id>` | Don't leave stale worktrees — they've caused real confusion for later sessions (see `docs/handoffs/`). |

---

## Recovery

If a task is stuck `in_progress` with no active worktree and no recent activity:

1. Check `.team/inbox/*.jsonl` for an escalation entry — a prior session may have already
   diagnosed why.
2. Investigate before reverting — read the worktree's actual diff and commit history if it
   still exists; don't assume abandonment.
3. If genuinely stale, document findings directly in the task JSON before reopening or
   re-completing it (see `docs/handoffs/HANDOFF-2026-07-02-SESSION-DOC-TEMPLATES.md` for a
   worked example of this exact recovery).

---

## Failure Handling

Stop after three repeated failures on the same fix. Write the failure to
`.team/inbox/billy.jsonl` and escalate (Rule 7 — Three Strike Rule). Do not retry indefinitely.

**An escalation is not permission to abandon the task — stay on it until it's resolved, not
moved past.** Resolving it means calling the advisor system (`ops/agent/advisor_manager.py`)
for a real analysis of what's actually blocking completion, not routing every escalation to
Billy by default — the advisor exists specifically so routine "why is this stuck" and
"is this evidence actually sufficient" decisions don't require Billy's direct input. Escalate
to Billy only when the advisor itself can't resolve it (e.g. a genuine policy/priority
decision, not a technical blocker).

---

## Related

- `agents/protocols/evidence-contract.md`
- `agents/protocols/AGENT_COMMUNICATION_PROTOCOL.md`
- `docs/governance/TASK_STATE_MACHINE.md`
- `ops/agent/task_manager.py`
