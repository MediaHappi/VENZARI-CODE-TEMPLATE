#!/usr/bin/env python3
"""Advanced typed closing gate for backend tasks."""

from base_gate import BaseGate


class GateBackend(BaseGate):
    layer_slug = "backend"
