# Wiki Index

**Project:** [FILL IN — your project name]
**Last rebuilt:** [FILL IN — YYYY-MM-DD]
**Engine:** `python3 ops/agent/wiki_search_engine.py`

This wiki is auto-generated and human-maintained. It captures incidents, entities, and
knowledge discovered during agent sessions.

---

## Incidents

| ID | Title | Severity | Date | Status |
|---|---|---|---|---|
| [INC-001] | [FILL IN] | [critical/high/medium/low] | [YYYY-MM-DD] | [open/resolved] |

See `docs/wiki/incidents/` for incident templates:
- `Timeout.md` — timeout / latency incidents
- `ConfigurationIncident.md` — misconfiguration incidents
- `LogicIncident.md` — logic / business rule failures
- `ResourceIncident.md` — resource exhaustion incidents

---

## Entities

Key system entities tracked in `docs/wiki/entities/`:

| Entity | Type | Description |
|---|---|---|
| [FILL IN] | [service/component/concept] | [FILL IN] |

---

## Knowledge Sources

Session learnings stored in `docs/wiki/sources/`:

| Source | Type | Added | Summary |
|---|---|---|---|
| [FILL IN] | [session/research/audit] | [YYYY-MM-DD] | [FILL IN] |

---

## How to Use

**Search:** `python3 ops/agent/wiki_search_engine.py query "your question"`
**Query API:** `python3 ops/agent/wiki_query_api.py`
**Add incident:** Create `docs/wiki/incidents/INC-XXX-title.md` using a template

---

*Wiki powered by VENZARI CODE — venzari.dev*
