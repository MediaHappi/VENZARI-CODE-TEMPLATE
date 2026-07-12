#!/usr/bin/env python3
"""Advanced typed closing gate for infrastructure tasks."""

from base_gate import BaseGate, CommandCheck, EvidenceRule, default_checks_for_layer


class GateInfrastructure(BaseGate):
    layer_slug = "infrastructure"

    def required_executable_checks(self):
        # The advanced-gate installer (task T0000000020) generalized this to a
        # keyword-matched pytest run, dropping real systemctl/curl verification
        # against the actual service being changed -- a real regression against
        # GOLDEN_RULES Rule 2 ("curl the affected endpoint... HTTP 200 is
        # verification"). Restored as an addition on top of the advanced base's
        # generic checks, not a replacement of them.
        checks = list(super().required_executable_checks())

        service = self._extract_service_name()
        if service:
            checks.append(CommandCheck(
                "service-active", ["systemctl", "is-active", service],
                f"service '{service}' mentioned in the task must be active", required=False, timeout=15,
            ))

        endpoint = self._extract_endpoint()
        if endpoint:
            checks.append(CommandCheck(
                "endpoint-health", ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", endpoint],
                f"endpoint '{endpoint}' mentioned in the task must respond", required=False, timeout=15,
            ))

        return checks

    def evidence_requirements(self):
        return list(super().evidence_requirements()) + [
            EvidenceRule(
                "service-or-endpoint-proof",
                "infrastructure work should show service state or endpoint health, not just a diff",
                keywords_any=("systemctl", "active", "running", "curl", "http", "200", "health", "docker", "container"),
                required=False,
            ),
        ]

    def _extract_service_name(self):
        desc = self.description.lower()
        if "service" not in desc and "deploy" not in desc:
            return None
        for word in desc.split():
            cleaned = word.rstrip(".,;:")
            if cleaned.isalpha() or "-" in cleaned or "_" in cleaned:
                if cleaned not in ("the", "a", "an", "service", "deploy"):
                    return cleaned
        return None

    def _extract_endpoint(self):
        for word in self.description.split():
            if word.startswith("http://") or word.startswith("https://"):
                return word.rstrip(",;:")
        return None
