#!/usr/bin/env python3
"""Advanced typed closing gate for uncategorized tasks."""

from base_gate import BaseGate


class GateUncategorized(BaseGate):
    layer_slug = "uncategorized"
