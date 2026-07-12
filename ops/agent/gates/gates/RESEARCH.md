# I0000000055 Research: Per-Layer Typed Gates Architecture

## Sources Researched

### 1. Open Policy Agent (OPA) - Resource-Type Gates
**Source:** github.com/open-policy-agent/conftest and OPA documentation
**Pattern:** Policy per resource type (Dockerfile, Kubernetes, Terraform manifests)
**Copied:** 
- One gate module per resource type = one gate module per task layer
- Manifest-agnostic base (all gates inherit from base class)
- Policy decision inputs structured as JSON/dict
- Fail-fast with specific reason (not just "blocked")

**Application to YOUR-PROJECT:**
- BaseGate: abstract class (like OPA's policy decision interface)
- 16 layer-specific gates: each returns {passed: bool, reason: str, evidence_checks: list}
- Each gate knows what verification it MUST run (systemctl, curl, pytest, git, DB queries)

### 2. pre-commit Framework - Hook Dispatch Architecture
**Source:** github.com/pre-commit/pre-commit
**Pattern:** Registry of independent hooks, each with language runner, entry point, files filter
**Copied:**
- Dispatcher pattern: central registry routes to specific handlers
- Each handler is independent and fails fast
- Handler error = gate fails (no swallowing exceptions)
- Handler runs its own verification command (not pattern-matched strings)

**Application to YOUR-PROJECT:**
- gate_dispatcher.py: central router with layer→gate_module mapping
- Each gate module is independent (gate_infrastructure.py, gate_backend.py, etc.)
- BaseGate defines contract: required_executable_checks() returns list of commands to run
- No pattern matching; gates run actual systemctl/curl/pytest/git commands

### 3. SonarSource Quality Gates - Hard Thresholds Per Metric
**Source:** SonarQube quality gate concepts
**Pattern:** Per-metric conditions with hard-fail thresholds (not fuzzy scoring)
**Copied:**
- evidence_requirements: structured per-layer (not generic keyword list)
- Each requirement specifies:
  - What must be proven (e.g., "service active", "all tests pass")
  - How to prove it (executable command)
  - Pass threshold (exit code 0, specific curl response, test count)
- No partial credit; all required checks must pass

**Application to YOUR-PROJECT:**
- gate_infrastructure.py requires: [systemctl check, curl /health, git verify]
- gate_testing.py requires: [pytest pass count ≥ threshold, coverage ≥ threshold]
- gate_backend.py requires: [git commit, tests pass, code review]
- Fail on ANY unmet requirement (not "3 out of 4 pass")

### 4. OpenHands Evaluation Harness - Execute, Don't Parse
**Source:** github.com/All-Hands-AI/OpenHands evaluation system
**Pattern:** Gates EXECUTE verification commands via subprocess, parse exit codes, compare outputs
**Copied:**
- verify_command: stored in gate as text, gate RUNS it via subprocess.run()
- Compare output to requirements (e.g., exit code == 0, output matches regex)
- Capture stdout/stderr for evidence/audit trail
- Fail if command fails (don't guess what agent meant)

**Application to YOUR-PROJECT:**
- BaseGate.run_executable_check(cmd: str) → {passed: bool, stdout: str, stderr: str, exit_code: int}
- gate_infrastructure.run_checks() runs ["systemctl status api-service", "curl -s -o /dev/null -w %{http_code} http://api/health", ...]
- Returns detailed proof (not just "yes it works")

## Architecture Decisions Made

### BaseGate Abstract Class
```python
class BaseGate:
    def __init__(self, task: dict): ...
    def required_executable_checks(self) -> List[str]: ...  # Commands to run
    def evidence_requirements(self) -> dict: ...  # Structured requirements
    def mandatory_test_command(self) -> str: ...  # Test agent must have run
    def run_check(cmd: str) -> CheckResult: ...  # Execute and capture
    def validate_all(self) -> GateResult: ...  # Main entry point
```

### Dispatcher Pattern
```python
# gate_dispatcher.py
LAYER_GATES = {
    'I': ('ops.agent.gates.gate_infrastructure', 'GateInfrastructure'),
    'B': ('ops.agent.gates.gate_backend', 'GateBackend'),
    'F': ('ops.agent.gates.gate_frontend', 'GateFrontend'),
    'T': ('ops.agent.gates.gate_testing', 'GateTesting'),
    # ... 12 more layers
}

def get_gate_for_layer(layer: str) -> BaseGate:
    # Dynamic import and instantiation
```

### Integration into task_manager.py
Replace invocation of closing_gate_v5 with:
```python
gate = get_gate_for_layer(task['layer'])
result = gate.validate_all()
if not result['passed']:
    fail_completion(...)
```

Keep closing_gate_v5 as secondary check (removed in I0000000058).

## Implementation Order (this task)

1. ✓ Research complete
2. Create ops/agent/gates/ package
3. Implement base_gate.py (BaseGate abstract class)
4. Implement gate_dispatcher.py
5. Implement gate_infrastructure.py (I layer)
6. Implement gate_backend.py (B layer)
7. Implement gate_documentation.py (E layer, note: E is doc layer per LAYER_NAME_TO_CODE)
8. Implement gate_testing.py (T layer)
9. Integrate dispatcher into task_manager.py complete_task()
10. Write comprehensive pytest suite
11. Verify no regressions (full ops/tests/ suite)

## What This Architecture Improves Over Copilot's Proposal

| Aspect | Copilot (PRODUCTION_HANDOFF C-003) | I0000000055 Implementation |
|---|---|---|
| Gate logic | Generic keyword matching (same for all layers) | Per-layer executable checks |
| Evidence validation | Pattern regex against evidence text | Actual command execution (systemctl, curl, git) |
| Gaming resistance | Fuzzy keyword match (easy to game) | Commands fail if system state is wrong (can't fake) |
| Failure modes | Pattern doesn't match = "probably bad" | Subprocess exit code = certain pass/fail |
| Audit trail | No proof that commands were actually run | Full output of each verification command |
| Extensibility | One giant keyword list | 16 independent modules, each can evolve independently |

---

**Date:** 2026-07-02
**Task:** I0000000055 (C-003 Fix)
**Source Code Location:** /opt/YOUR-PROJECT/ops/agent/gates/
