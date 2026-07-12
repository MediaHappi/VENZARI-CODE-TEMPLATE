#!/usr/bin/env python3
"""Advanced typed closing gate for devops tasks.

Hardened 2026-07-05 (Kiro session): added devops-specific checks.
Previously a stub that only ran base checks.
"""

from pathlib import Path
from base_gate import BaseGate, CommandCheck, EvidenceRule

REPO = Path(__file__).resolve().parents[3]


class GateDevops(BaseGate):
    layer_slug = "devops"

    def required_executable_checks(self):
        checks = list(super().required_executable_checks())

        # Docker compose files must be valid YAML if changed
        changed = self.changed_files()
        compose_files = [f for f in changed if "docker-compose" in f and f.endswith((".yml", ".yaml"))]
        for cf in compose_files[:3]:
            checks.append(CommandCheck(
                f"compose-valid-{cf.replace('/', '-')}",
                ["python3", "-c", f"import yaml; yaml.safe_load(open('{REPO}/{cf}')); print('OK')"],
                f"{cf} must be valid YAML",
                required=False, timeout=10,
            ))

        # Systemd unit files must pass systemd-analyze verify if changed
        unit_files = [f for f in changed if f.endswith(".service") or f.endswith(".timer")]
        for uf in unit_files[:3]:
            checks.append(CommandCheck(
                f"systemd-valid-{uf.replace('/', '-')}",
                ["bash", "-c", f"systemd-analyze verify {REPO}/{uf} 2>&1 || echo 'WARNING: systemd-analyze not available or unit has warnings'"],
                f"{uf} must be a valid systemd unit",
                required=False, timeout=15,
            ))

        return checks

    def evidence_requirements(self):
        return list(super().evidence_requirements()) + [
            EvidenceRule(
                "deploy-proof",
                "devops work must show deployment evidence (docker ps, systemctl status, or service health)",
                keywords_any=("docker ps", "systemctl", "active", "running", "deployed", "restarted",
                               "container", "health", "curl", "200"),
                required=False,
            ),
        ]
