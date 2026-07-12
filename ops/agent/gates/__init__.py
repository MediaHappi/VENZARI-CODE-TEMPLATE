"""
ops/agent/gates - Per-layer typed closing gates package

This package implements the architectural upgrade (I0000000055) that replaces
the generic V4/V5 closing gates with layer-specific gates that:

1. RUN executable checks (systemctl, curl, pytest, git) instead of grepping text
2. Have structured evidence requirements per layer
3. Are resistant to gaming (read immutable snapshots, not mutable fields)
4. Provide detailed audit trails (full command output + exit codes)

Each layer (Infrastructure, Backend, Testing, etc.) gets its own gate module
that inherits from BaseGate and implements:
- required_executable_checks(): list of commands to run
- evidence_requirements(): structured requirements dict
- mandatory_test_command(): the verification test command

The dispatcher routes task layers to the appropriate gate module.
"""

__version__ = "1.0.0"
__all__ = [
    'base_gate',
    'gate_dispatcher',
    'gate_infrastructure',
    'gate_backend',
    'gate_documentation',
    'gate_testing',
]
