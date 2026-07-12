#!/usr/bin/env python3
"""
Gate Dispatcher: Route layer codes to per-layer gate modules.
Maps task layer to specific gate class using dynamic import.

Task I0000000066 (2026-07-02): this module previously had three compounding bugs that
meant the typed-gate system never actually enforced anything for most tasks:
1. LAYER_GATES had 'U' and 'X' swapped relative to the canonical LAYER_CODES in
   task_numbering.py (U=autonomous, X=uncategorized there; this file had them backwards).
2. get_gate_for_layer() hard-coded implemented_gates = {'I', 'B', 'E', 'T'} and raised
   NotImplementedError for the other 12 layers even though all 12 have real, working
   BaseGate subclasses (confirmed by reading them directly — not stubs).
3. validate_task_with_typed_gate() resolved the layer code via layer[0].upper() instead
   of the canonical name->code mapping, which is wrong for any layer whose name's first
   letter doesn't match its assigned single-letter code — at least 7 of 16 layers
   (data->A, training->R, autonomous->U, monitoring->L, telegram->C, dashboard->H,
   documentation->E all have a first letter that collides with a DIFFERENT layer's code).
All three are fixed here. See task_manager.py's call site for the companion fix (it never
checked this function's returned 'passed' field before).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from task_numbering import LAYER_NAME_TO_CODE, LAYER_CODES
except ImportError:
    # Fallback if task_numbering.py's location changes — keep this file self-sufficient.
    LAYER_CODES = {
        "I": "infrastructure", "B": "backend", "F": "frontend", "T": "testing",
        "S": "security", "D": "devops", "A": "data", "M": "memory", "R": "training",
        "U": "autonomous", "O": "orchestration", "L": "monitoring", "C": "telegram",
        "H": "dashboard", "E": "documentation", "X": "uncategorized",
    }
    LAYER_NAME_TO_CODE = {v: k for k, v in LAYER_CODES.items()}

# Legacy/placeholder layer names that aren't in LAYER_CODES but need a home so they
# route through a typed gate instead of falling back to the legacy V4/V5 closing gate.
# Built from an audit of every distinct layer value across .tasks/*.json (task
# I0000000066, 2026-07-02) — covers every non-canonical value seen on an ACTIVE
# (pending/in_progress) task. Genuinely malformed values seen on a handful of active
# tasks ('--layer', '--description', '--skill' — symptomatic of a task-creation CLI
# parsing bug, a separate issue) are deliberately NOT aliased here; those tasks correctly
# fall back to legacy V5 until that underlying data-quality bug is fixed at the source.
_LAYER_ALIASES = {
    'unassigned': 'X',      # create_task()'s own default parameter value
    'uncategorized': 'X',
    'general': 'X',
    'autonomy': 'U',        # naming variant of 'autonomous'
    'intelligence': 'X',    # legacy pre-16-layer-scheme value, no clean modern equivalent
}

# Layer code to (module, class_name) mapping — matches LAYER_CODES exactly.
LAYER_GATES = {
    'I': ('gate_infrastructure', 'GateInfrastructure'),
    'B': ('gate_backend', 'GateBackend'),
    'F': ('gate_frontend', 'GateFrontend'),
    'T': ('gate_testing', 'GateTesting'),
    'S': ('gate_security', 'GateSecurity'),
    'D': ('gate_devops', 'GateDevops'),
    'A': ('gate_data', 'GateData'),
    'M': ('gate_memory', 'GateMemory'),
    'R': ('gate_training', 'GateTraining'),
    'U': ('gate_autonomous', 'GateAutonomous'),
    'O': ('gate_orchestration', 'GateOrchestration'),
    'L': ('gate_monitoring', 'GateMonitoring'),
    'C': ('gate_telegram', 'GateTelegram'),
    'H': ('gate_dashboard', 'GateDashboard'),
    'E': ('gate_documentation', 'GateDocumentation'),
    'X': ('gate_uncategorized', 'GateUncategorized'),
}

assert set(LAYER_GATES.keys()) == set(LAYER_CODES.keys()), (
    "LAYER_GATES must cover exactly the same codes as task_numbering.py's LAYER_CODES"
)


def resolve_layer_code(task: dict) -> str:
    """Resolve a task's single-letter layer code using the canonical mapping, not a
    first-letter guess. Prefers task['layer_code'] if the caller already computed it
    (task_manager.py does); falls back to LAYER_NAME_TO_CODE by layer name; falls back
    to the legacy-layer aliases (unassigned/general/etc.); raises if none resolve."""
    injected = task.get('layer_code')
    if injected and injected.upper() in LAYER_GATES:
        return injected.upper()

    layer_name = (task.get('layer') or '').strip().lower()
    if layer_name in LAYER_NAME_TO_CODE:
        return LAYER_NAME_TO_CODE[layer_name]
    if layer_name in _LAYER_ALIASES:
        return _LAYER_ALIASES[layer_name]

    raise ValueError(
        f"Cannot resolve a layer code for layer='{task.get('layer')!r}'. "
        f"Known layer names: {', '.join(sorted(LAYER_NAME_TO_CODE.keys()))}. "
        f"Known aliases: {', '.join(sorted(_LAYER_ALIASES.keys()))}."
    )


def get_gate_for_layer(layer_code: str, task: dict):
    """
    Dynamically load and instantiate the gate for a given layer.

    Args:
        layer_code: single character layer code (I, B, F, T, etc.)
        task: task dict to pass to gate __init__

    Returns:
        Gate instance (subclass of BaseGate)

    Raises:
        ValueError: if layer_code unknown
        ImportError: if gate module cannot be imported
    """
    if layer_code not in LAYER_GATES:
        raise ValueError(
            f"Unknown layer code: '{layer_code}'. "
            f"Valid codes: {', '.join(sorted(LAYER_GATES.keys()))}"
        )

    module_name, class_name = LAYER_GATES[layer_code]

    # All 16 layer gates are real, working BaseGate subclasses (task I0000000066 removed
    # the stale 'only I/B/E/T are implemented' restriction that used to live here — every
    # gate file was already implemented, just excluded from this hardcoded set).

    # Dynamic import
    gates_package = Path(__file__).parent
    sys.path.insert(0, str(gates_package))

    try:
        module = __import__(module_name)
        gate_class = getattr(module, class_name)
        return gate_class(task)
    except ImportError as e:
        raise ImportError(f"Cannot import gate module '{module_name}': {e}")
    except AttributeError as e:
        raise ImportError(f"Gate class '{class_name}' not found in '{module_name}': {e}")
    finally:
        if str(gates_package) in sys.path:
            sys.path.remove(str(gates_package))


def validate_task_with_typed_gate(task: dict) -> dict:
    """
    Main entry point: validate task using its layer-specific gate.

    Args:
        task: task dict with 'layer' field (and optionally a pre-computed 'layer_code')

    Returns:
        {
            'passed': bool,
            'gate_type': str,  # layer code
            'gate_name': str,  # human-readable name
            'failures': list,  # [(check_name, reason), ...]
            'message': str,    # formatted error or success message
        }

    IMPORTANT: callers MUST check the returned 'passed' field. This function does not
    raise on a failing gate — it returns passed=False. (task_manager.py's call site was
    fixed in I0000000066 to actually do this after not doing so for an unknown length
    of time.)
    """
    layer = task.get('layer', 'unknown')

    try:
        layer_code = resolve_layer_code(task)
        gate = get_gate_for_layer(layer_code, task)
        result = gate.validate_all()
        gate_name = LAYER_GATES[layer_code][1]

        if result.passed:
            return {
                'passed': True,
                'gate_type': layer_code,
                'gate_name': gate_name,
                'failures': [],
                'message': f"✓ {layer_code} gate ({gate_name}): All checks passed"
            }
        else:
            return {
                'passed': False,
                'gate_type': layer_code,
                'gate_name': gate_name,
                'failures': result.failures,
                'message': gate.format_failure_message(result)
            }

    except Exception as e:
        # Gate loading/dispatch error — fail closed, not open. A dispatch error means
        # we could not verify the task, which is not the same as verifying it passed.
        return {
            'passed': False,
            'gate_type': layer,
            'gate_name': 'Error',
            'failures': [('gate_dispatch', str(e))],
            'message': f"⛔ Gate dispatch error for layer {layer!r}: {e}"
        }
