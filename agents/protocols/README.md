# agents/protocols/

**Status:** ACTIVE — Inter-agent communication protocol definitions  
**Owner:** [YOUR-AI-NAME] Orchestrator  

---

## Contents

| File | Purpose |
|---|---|
| AGENT_COMMUNICATION_PROTOCOL.md | Message format, mailbox routing, task claiming protocol |

---

## Protocol Rules

1. All agent-to-agent messages go through `.team/inbox/<agent>.jsonl`
2. Tasks are claimed atomically via `ops/agent/claim.sh` (uses fcntl.LOCK_EX)
3. No agent polls another agent directly — only via task queue or mailbox
4. Messages are JSONL, one object per line, append-only
5. Completed tasks always include an `evidence` string (not "should work")

---

## Adding a New Protocol

1. Create `<PROTOCOL_NAME>.md` in this directory
2. Reference from PROJECT_OVERLAY.md in agents/
3. Add to this README's Contents table
