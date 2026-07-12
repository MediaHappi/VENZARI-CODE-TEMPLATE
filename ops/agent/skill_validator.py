#!/usr/bin/env python3
"""
Skill Validator — fuzzy matching for task completion skills
Prevents deadlock from skill typos via similarity matching at 0.8 threshold
"""
import difflib
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
try:
    from incident_detector import Incident, IncidentType, IncidentSeverity
    from finding_creator import FindingCreator
    from opensre_findings_format import OpenSREFindingsExporter
    HAS_FINDINGS = True
except ImportError:
    HAS_FINDINGS = False


@dataclass
class SkillMatch:
    """Result of skill matching"""
    matched: bool
    skill_used: str
    skill_required: str
    confidence: float
    suggestion: Optional[str] = None
    exact: bool = False


class SkillValidator:
    """Validate and suggest skills using fuzzy matching"""

    CONFIDENCE_THRESHOLD = 0.8  # 80% similarity required

    def __init__(self, required_skills: List[str]):
        """Initialize with list of required skills"""
        self.required_skills = [s.lower().strip() for s in required_skills]

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0.0 to 1.0)"""
        matcher = difflib.SequenceMatcher(None, s1.lower(), s2.lower())
        return matcher.ratio()

    def validate(self, skill_used: str) -> SkillMatch:
        """
        Validate a skill against required skills.
        Returns SkillMatch with confidence score and suggestions.
        """
        if not skill_used:
            return SkillMatch(
                matched=False,
                skill_used="",
                skill_required=self.required_skills[0] if self.required_skills else "",
                confidence=0.0,
                suggestion="Skill parameter required"
            )

        skill_used_lower = skill_used.lower().strip()

        # Check for exact matches (case-insensitive)
        for required in self.required_skills:
            if skill_used_lower == required:
                return SkillMatch(
                    matched=True,
                    skill_used=skill_used,
                    skill_required=required,
                    confidence=1.0,
                    exact=True
                )

        # Check for substring matches (both directions)
        for required in self.required_skills:
            if skill_used_lower in required or required in skill_used_lower:
                return SkillMatch(
                    matched=True,
                    skill_used=skill_used,
                    skill_required=required,
                    confidence=0.95,
                    exact=False
                )

        # Check for fuzzy matches using similarity
        best_match = None
        best_confidence = 0.0

        for required in self.required_skills:
            sim = self._similarity(skill_used_lower, required)
            if sim > best_confidence:
                best_confidence = sim
                best_match = required

        if best_match and best_confidence >= self.CONFIDENCE_THRESHOLD:
            return SkillMatch(
                matched=True,
                skill_used=skill_used,
                skill_required=best_match,
                confidence=best_confidence,
                suggestion=f"Close match (similarity: {best_confidence:.1%}). Did you mean '{best_match}'?",
                exact=False
            )

        # No good match found
        suggestions = self._generate_suggestions(skill_used_lower)
        return SkillMatch(
            matched=False,
            skill_used=skill_used,
            skill_required=self.required_skills[0] if self.required_skills else "",
            confidence=best_confidence,
            suggestion=suggestions
        )

    def _generate_suggestions(self, skill_used: str) -> str:
        """Generate helpful suggestions for mismatched skill"""
        if not self.required_skills:
            return "No required skills defined"

        # Find closest matches
        matches = []
        for required in self.required_skills:
            sim = self._similarity(skill_used, required)
            matches.append((required, sim))

        matches.sort(key=lambda x: x[1], reverse=True)

        suggestions = f"Skill '{skill_used}' doesn't match required skills. "
        suggestions += f"Required: {', '.join(self.required_skills)}"

        if matches[0][1] >= 0.7:
            suggestions += f". Did you mean '{matches[0][0]}'?"

        return suggestions

    def get_closest_matches(self, skill_used: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """Return top N closest skill matches"""
        matches = []
        skill_used_lower = skill_used.lower().strip()

        for required in self.required_skills:
            sim = self._similarity(skill_used_lower, required)
            matches.append((required, sim))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_n]

    def list_required_skills(self) -> List[str]:
        """Return list of required skills"""
        return self.required_skills


# Integration function for complete_task()
def validate_skill_with_fuzzy_matching(skill_used: str, required_skills: List[str]) -> Tuple[bool, str]:
    """
    Validate skill with fuzzy matching.
    Returns (is_valid, message)
    """
    if not required_skills:
        return True, ""

    validator = SkillValidator(required_skills)
    match = validator.validate(skill_used)

    if match.matched:
        if match.exact:
            return True, f"✓ Exact skill match: {match.skill_used}"
        else:
            return True, f"✓ Fuzzy match ({match.confidence:.0%}): {match.skill_used} ≈ {match.skill_required}"
    else:
        return False, f"✗ Skill mismatch: {match.suggestion}"
