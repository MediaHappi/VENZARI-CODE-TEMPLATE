# ops/agent/ Module Index

Auto-generated 2026-07-06 (task YOUR-AI-CONSOLIDATION-001).

This directory contains the YOUR-AI agent runtime — all modules loaded by `module_loader.py`.

## Core Infrastructure
| Module | Purpose |
|--------|---------|
| `task_manager.py` | SSOT task lifecycle — claim, complete, gate enforcement |
| `config.py` | Centralized IPs/ports/timeouts (all env-var overridable) |
| `distributed_lock.py` | Redis 60s TTL + fcntl fallback distributed locking |
| `mailbox.py` | Async agent communication via JSONL files |
| `module_loader.py` | Activates and integrates all agent modules |

## Memory Layers
| Module | Purpose |
|--------|---------|
| `inject_context.py` | 6-layer context injection at task claim time (`--dry-run` for blast-radius) |
| `memory-governance.py` | Write operational experience to L3 after task completion |
| `memory_client.py` | → see `interfaces/shared/universal_client.py` (unified) |
| `chromadb_adapter.py` | L3 ChromaDB adapter (:8001) |
| `claude_mem_adapter.py` | L3 claude-mem service adapter (:37877) |
| `codegraph_adapter.py` | L4 code intelligence adapter |
| `memory_write.py` | Low-level L3 write |
| `memory_aging.py` | Scans + ages stale L3 entries (>30d) |
| `stale_memory_detector.py` | Alerts on stale memory layers |
| `wire_all_memory_layers.py` | Persist task completion to all 5 memory layers |

## Advisor System
| Module | Purpose |
|--------|---------|
| `advisor_manager.py` | Advisor lifecycle + L3 write on completion (W0000000002) |
| `advisor_integration.py` | Auto-call advisor for complex/approval tasks |
| `advisor_deep_analyzer.py` | Architectural reasoning layer |
| `advisor_type_router.py` | Route tasks to specialized advisor types |
| `advisor_prompt_templates.py` | Task-specific advisor prompts |
| `advisor_wiki_generator.py` | Auto-generate wiki from advisor findings |
| `advisor_validation.py` | Close advisor feedback loop |

## Enforcement Gates
| Module | Purpose |
|--------|---------|
| `closing_gate_v5_real_work.py` | Active closing gate — real work enforcement |
| `task_claim_gate_v1.py` | Start-of-task enforcement |
| `approval_gate.py` | Tiered approval for MEDIUM/HIGH tasks |
| `completion_validator.py` | Unified task completion validation |
| `session_enforcement.py` | Session-level rule enforcement |

## Skill System
| Module | Purpose |
|--------|---------|
| `skill_loader.py` | Unified index of all available skills |
| `skill_matcher.py` | Match tasks to skills |
| `skill_router.py` | Fast capability-tag index |
| `skill_validator.py` | Fuzzy skill matching for closing |
| `scan_skills.py` | Auto-tag skills by scope + dependencies |

## Testing
| Module | Purpose |
|--------|---------|
| `../tests/test_failover_chain_T00004.py` | 7-test failover chain Local→Groq→Mistral→OpenRouter |

## Key Design Decisions
- All hardcoded IPs/ports/timeouts → use `config.py` (task I00008)
- All interfaces (Slack/Telegram/Dashboard) → use `interfaces/shared/universal_client.py` (task 1737)
- L3 writes are **non-blocking** — failures log warnings, never crash task flow
- Gate system is layered: claim → pre-flight → execution → closing → L5 git-archive
