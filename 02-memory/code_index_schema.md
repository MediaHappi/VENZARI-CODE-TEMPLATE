# [YOUR-AI-NAME] Code Intelligence — ChromaDB Collection Schema
**Last updated:** 2026-05-27
**Status:** ACTIVE — defines jeanne_code_symbols collection

---

## Overview

[YOUR-AI-NAME]'s code intelligence index stores Python symbol relationships in ChromaDB, enabling agents to answer "what calls X?" and "what breaks if Y changes?" in one query instead of multiple file reads.

Benchmark reference (from codegraph): pre-indexing symbol relationships reduces agent tool calls by ~70% vs grep-and-read patterns.

**No tree-sitter required** — stdlib `ast` module is sufficient for [YOUR-AI-NAME]'s Python-dominant codebase.

---

## Collection: `jeanne_code_symbols`

**ChromaDB host:** `http://127.0.0.1:8001` ([your-vps-address]

### Document format
```
<symbol_type> <symbol_name> in <file_path>:<line_number>
Calls: [func1, func2]
Called by: [caller1, caller2]
Docstring (first line): <docstring or empty>
```

This text is the semantic search target — agents can find symbols by natural language query.

### Metadata fields

| Field | Type | Description | Example |
|---|---|---|---|
| `symbol_type` | string | `function`, `class`, `method`, `route` | `"function"` |
| `symbol_name` | string | The symbol name as it appears in code | `"claim_task"` |
| `file_path` | string | Repo-relative path | `"ops/agent/task_manager.py"` |
| `line_number` | integer | Line where the symbol is defined | `116` |
| `calls` | string (JSON array) | Functions/methods this symbol calls | `'["save_task", "load_task", "is_unblocked"]'` |
| `called_by` | string (JSON array) | Symbols that call this one | `'["run_task", "main"]'` |
| `layer` | string | [YOUR-AI-NAME] layer (00–05 or ops or agents) | `"ops"` |
| `indexed_at` | string | ISO 8601 UTC timestamp of last indexing | `"2026-05-27T10:00:00Z"` |

Note: `calls` and `called_by` are JSON-encoded strings (ChromaDB metadata constraint).

### Document ID format
```
sha256(<file_path>:<symbol_name>:<line_number>)[:16]
```
Stable across re-indexes as long as the symbol doesn't move.

---

## Indexer: `code_index.py`

**Location:** `/opt/YOUR-PROJECT/ops/agent/code_index.py`

**Usage:**
```bash
# Index the full YOUR-PROJECT repo
python3 /opt/YOUR-PROJECT/ops/agent/code_index.py index /opt/YOUR-PROJECT

# Check indexed symbol count
python3 /opt/YOUR-PROJECT/ops/agent/code_index.py status
```

**Extraction scope:**
- Functions (top-level and nested)
- Classes
- Methods (within classes)
- Call relationships extracted from AST `ast.Call` nodes

**Files indexed:** `*.py` files in the YOUR-PROJECT repo, excluding:
- `.git/`
- `.worktrees/`
- `__pycache__/`
- `venv/`, `env/`

---

## Query Tool: `code_query.py`

**Location:** `/opt/YOUR-PROJECT/ops/agent/code_query.py`

**Usage:**
```bash
# Semantic search
python3 code_query.py search "claim task atomically"

# Find a specific symbol
python3 code_query.py find claim_task

# Find all symbols in a file
python3 code_query.py file ops/agent/task_manager.py

# Impact analysis: what breaks if this changes?
python3 code_query.py impact claim_task
```

The `impact` command returns symbols in `called_by` metadata — agents use this before editing a function to understand downstream risk.

---

## Post-Commit Hook

**Location:** `/opt/YOUR-PROJECT/ops/setup/post-commit-hook.sh`

Automatically re-indexes modified Python files after every commit:
```bash
# Install
cp /opt/YOUR-PROJECT/ops/setup/post-commit-hook.sh /opt/YOUR-PROJECT/.git/hooks/post-commit
chmod +x /opt/YOUR-PROJECT/.git/hooks/post-commit
```

The hook runs `code_index.py index` in the background — it does not block the commit.

---

## Impact Analysis Pattern

Before editing any function, agents should run:
```bash
python3 /opt/YOUR-PROJECT/ops/agent/code_query.py impact <function_name>
```

If `called_by` contains production-path functions (e.g., `claim_task`, `complete_task`, `send`), the edit requires the build-and-verify skill and potentially `requires_review: true` on the task.

---

## Operational Notes

### Re-indexing schedule
- Automatically: on every `git commit` via post-commit hook
- Manually: `python3 code_index.py index /opt/YOUR-PROJECT` (takes ~5 seconds for the full repo)

### ChromaDB unavailability
If ChromaDB is unreachable, `code_query.py` exits with a clear error. Agents fall back to grep and file-reading. The index is a performance optimization, not a hard dependency.

### Index staleness
The index is stale between commits. For files edited but not yet committed, use grep to find symbols — then commit and the index auto-updates.
