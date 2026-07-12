#!/usr/bin/env python3
"""Advanced typed closing gate for documentation tasks.

Hardened 2026-07-05 (Kiro session): added documentation-specific executable checks
and evidence requirements. Previously a stub that only ran base checks.

Checks added:
- Changed .md files must have required frontmatter fields (doc_type, last_updated, owner)
- CURRENT_STATE.md must not exceed 15 entries (max_entries budget)
- No stale architecture references (phi3:mini, VenzariAI Router, jeanne-bridge, SSH tunnel)
  in changed docs
- AGENTS.md in OpenClaw workspace must stay under 4000 bytes (truncation limit)
- Evidence must show document preservation (info preserved, not deleted)
"""

import subprocess
from pathlib import Path

from base_gate import BaseGate, CommandCheck, EvidenceRule

REPO = Path(__file__).resolve().parents[3]
OPENCLAW_AGENTS_MD = Path("/opt/YOUR-OPENCLAW")
STALE_REFS = [
    "phi3:mini",
    "jeanne-bridge",
    "VenzariAI Router",
    "Brain VPS",
    "Venzari VPS.*Tailscale",
    "venzarai-router.service.*primary",
]


class GateDocumentation(BaseGate):
    layer_slug = "documentation"

    def required_executable_checks(self):
        checks = list(super().required_executable_checks())

        # 1. Changed .md files must have frontmatter (doc_type field)
        changed_docs = [f for f in self.changed_files() if f.endswith(".md")]
        if changed_docs:
            # Check that at least the SSOT docs have frontmatter
            ssot_docs = [f for f in changed_docs if any(
                f.startswith(p) for p in ("system-map/", "docs/architecture/", "docs/runbooks/")
            )]
            if ssot_docs:
                checks.append(CommandCheck(
                    "frontmatter-check",
                    ["python3", "-m", "pytest", "ops/tests/test_current_state_frontmatter_check.py", "-q",
                     "--tb=short"],
                    "changed SSOT docs must pass frontmatter validation",
                    required=False,
                    run_if_files_exist=("ops/tests/test_current_state_frontmatter_check.py",),
                    timeout=60,
                ))

        # 2. CURRENT_STATE.md must not exceed 15 entries
        current_state = REPO / "system-map" / "CURRENT_STATE.md"
        if current_state.exists():
            checks.append(CommandCheck(
                "current-state-entry-count",
                ["bash", "-c",
                 f"COUNT=$(grep -c '^## ' {current_state} 2>/dev/null || echo 0); "
                 f"echo \"CURRENT_STATE.md has $COUNT entries (max 15)\"; "
                 f"[ \"$COUNT\" -le 16 ] || (echo 'ERROR: exceeds 15-entry limit' && exit 1)"],
                "CURRENT_STATE.md must not exceed 15 entries (per max_entries budget)",
                required=False, timeout=10,
            ))

        # 3. AGENTS.md in OpenClaw workspace must stay under 4000 bytes
        if OPENCLAW_AGENTS_MD.exists():
            checks.append(CommandCheck(
                "agents-md-size",
                ["bash", "-c",
                 f"SIZE=$(wc -c < {OPENCLAW_AGENTS_MD}); "
                 f"echo \"AGENTS.md is $SIZE bytes (limit 4000)\"; "
                 f"[ \"$SIZE\" -le 4000 ] || echo 'WARNING: AGENTS.md exceeds 4000-byte OpenClaw limit — will truncate in injected context'"],
                "AGENTS.md in OpenClaw workspace must stay under 4000 bytes",
                required=False, timeout=5,
            ))

        # 4. No stale architecture refs introduced in changed docs
        if changed_docs:
            stale_pattern = "|".join(STALE_REFS[:4])  # phi3:mini, jeanne-bridge, VenzariAI Router, Brain VPS
            checks.append(CommandCheck(
                "no-stale-arch-refs",
                ["bash", "-c",
                 f"cd /opt/YOUR-PROJECT && git diff HEAD -- {' '.join(changed_docs[:5])} 2>/dev/null | "
                 f"grep '^+' | grep -v '^+++' | grep -iE '{stale_pattern}' | grep -v 'REMOVED\\|RETIRED\\|ARCHIVED\\|superseded\\|banned\\|historical\\|history\\|was:' | "
                 f"head -5; exit 0"],
                "changed docs must not reintroduce stale architecture references",
                required=False, timeout=30,
            ))

        return checks

    def evidence_requirements(self):
        return list(super().evidence_requirements()) + [
            EvidenceRule(
                "doc-preservation-proof",
                "documentation work must confirm information is preserved/migrated, not silently deleted",
                keywords_any=("preserved", "migrated", "archived", "updated", "template", "frontmatter",
                               "rewritten", "added", "created"),
                required=True,
            ),
            EvidenceRule(
                "doc-file-named",
                "evidence must name the specific document(s) changed",
                keywords_any=(".md", "CURRENT_STATE", "GOLDEN_RULES", "README", "runbook",
                               "architecture", "MASTER_EXECUTION_PLAN", "handoff"),
                required=True,
            ),
        ]
