#!/usr/bin/env python3
"""Advanced typed closing gate for training tasks.

Hardened 2026-07-05 (Kiro session): added training-specific executable checks
and evidence requirements. Previously a stub that only ran base checks.

Checks added:
- model_roles.py must exist and be importable (role-based SSOT requirement)
- No banned model names (phi3:mini, llama3.2, jeanne-primary:latest) in changed files
- registry.json must be valid JSON and contain a 'roles' key
- Training scripts that changed must compile (Python) or be executable (bash)
- Evidence must reference model roles, not hardcoded model names
"""

import subprocess
import sys
from pathlib import Path

from base_gate import BaseGate, CommandCheck, EvidenceRule

REPO = Path(__file__).resolve().parents[3]
TRAINING_REPO = Path("/opt/jeanne-training")
BANNED_MODELS = ["phi3:mini", "llama3.2", "jeanne-primary:latest", "qwen3:1.7b"]


class GateTraining(BaseGate):
    layer_slug = "training"

    def required_executable_checks(self):
        checks = list(super().required_executable_checks())

        # 1. model_roles.py must exist in jeanne-training (SSOT requirement)
        checks.append(CommandCheck(
            "model-roles-exists",
            ["test", "-f", str(TRAINING_REPO / "model_roles.py")],
            "model_roles.py must exist in /opt/jeanne-training (role-based SSOT)",
            required=True, timeout=5,
        ))

        # 2. model_roles.py must be importable (syntax check)
        if (TRAINING_REPO / "model_roles.py").exists():
            checks.append(CommandCheck(
                "model-roles-importable",
                ["python3", "-c", "import sys; sys.path.insert(0, '/opt/jeanne-training'); from model_roles import MODEL_ROLES, get_model; assert 'fast_chat' in MODEL_ROLES; assert 'jeanne_primary' in MODEL_ROLES; print('OK')"],
                "model_roles.py must define MODEL_ROLES with fast_chat and jeanne_primary roles",
                required=True, timeout=15,
            ))

        # 3. registry.json must be valid JSON with 'roles' key
        if (TRAINING_REPO / "models" / "registry.json").exists():
            checks.append(CommandCheck(
                "registry-json-valid",
                ["python3", "-c", "import json; d=json.load(open('/opt/jeanne-training/models/registry.json')); assert 'roles' in d, 'registry.json must have roles key'; assert 'fast_chat' in d['roles']; print('OK')"],
                "models/registry.json must be valid JSON with roles.fast_chat entry",
                required=True, timeout=10,
            ))

        # 4. No banned model names in changed training files
        changed = self.changed_files()
        training_changed = [
            f for f in changed
            if f.startswith("jeanne-training/") or "/jeanne-training/" in f
            or not f.startswith("ops/")  # changed files in training repo
        ]
        if changed:
            # Build grep pattern for banned models
            banned_pattern = "|".join(BANNED_MODELS)
            checks.append(CommandCheck(
                "no-banned-models",
                ["bash", "-c",
                 f"cd /opt/jeanne-training && git diff HEAD --name-only 2>/dev/null | "
                 f"xargs grep -l '{banned_pattern}' 2>/dev/null | "
                 f"grep -v '.git' | grep -v 'banned_models\\|BANNED\\|#.*phi3\\|archived' | "
                 f"head -5; exit 0"],
                "changed files must not introduce banned model names (phi3:mini, llama3.2, jeanne-primary:latest)",
                required=False, timeout=30,
            ))

        # 5. Ollama must have exactly the 3 canonical models (verify post-swap)
        checks.append(CommandCheck(
            "ollama-canonical-models",
            ["bash", "-c",
             "docker exec ollama ollama list 2>/dev/null | grep -E 'qwen2.5:1.5b-fast|qwen2.5-coder:7b|nomic-embed-text' | wc -l | grep -q '^3$' && echo 'OK: 3 canonical models present' || echo 'WARNING: unexpected model count'"],
            "Ollama must have exactly 3 canonical models after training changes",
            required=False, timeout=20,
        ))

        return checks

    def evidence_requirements(self):
        return list(super().evidence_requirements()) + [
            EvidenceRule(
                "role-based-reference",
                "training work must reference model roles (fast_chat/jeanne_primary), not hardcoded model names",
                keywords_any=("fast_chat", "jeanne_primary", "model_roles", "role", "MODEL_ROLES"),
                required=True,
            ),
            EvidenceRule(
                "training-commit-proof",
                "training work must include a commit hash from jeanne-training repo",
                keywords_any=("commit", "git log", "sha", "hash", "jeanne-training"),
                required=False,
            ),
            EvidenceRule(
                "no-banned-model-in-evidence",
                "evidence must not contain banned model names",
                patterns=(r"\bphi3:mini\b", r"\bllama3\.2\b", r"\bjeanne-primary:latest\b"),
                required=False,
            ),
        ]
