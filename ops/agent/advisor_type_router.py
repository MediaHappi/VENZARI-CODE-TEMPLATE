#!/usr/bin/env python3
"""
Advisor Type Router — Route tasks to specialized advisor types (Task I0000000029)

Maps task domains/types to specialized advisor capabilities:
- SecurityAdvisor: security, auth, permissions, vulnerability
- PerformanceAdvisor: performance, optimization, scalability, bottleneck
- ArchitectureAdvisor: architecture, design, patterns, large refactors
- ReliabilityAdvisor: reliability, fault tolerance, recovery, testing
- IntegrationAdvisor: integrations, APIs, webhooks, data pipelines
- DevOpsAdvisor: infrastructure, deployment, CI/CD, ops automation
- DataAdvisor: data modeling, migrations, analytics, databases
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class AdvisorType(Enum):
    """Specialized advisor types"""
    SECURITY = "security"           # Security & authentication
    PERFORMANCE = "performance"     # Optimization & scaling
    ARCHITECTURE = "architecture"   # System design & patterns
    RELIABILITY = "reliability"     # Testing & fault tolerance
    INTEGRATION = "integration"     # APIs & webhooks
    DEVOPS = "devops"               # Infrastructure & deployment
    DATA = "data"                   # Databases & data pipelines
    GENERAL = "general"             # Fallback for unspecialized


@dataclass
class AdvisorTypeMatch:
    """Match result from routing"""
    primary_type: AdvisorType
    alternative_types: List[AdvisorType]
    confidence: float  # 0.0 to 1.0
    reason: str


# Domain → Advisor Type Mappings
DOMAIN_TO_ADVISOR_TYPE = {
    "security": AdvisorType.SECURITY,
    "auth": AdvisorType.SECURITY,
    "permissions": AdvisorType.SECURITY,
    "vulnerability": AdvisorType.SECURITY,
    "encryption": AdvisorType.SECURITY,

    "performance": AdvisorType.PERFORMANCE,
    "optimization": AdvisorType.PERFORMANCE,
    "scaling": AdvisorType.PERFORMANCE,
    "bottleneck": AdvisorType.PERFORMANCE,
    "profiling": AdvisorType.PERFORMANCE,

    "architecture": AdvisorType.ARCHITECTURE,
    "design": AdvisorType.ARCHITECTURE,
    "patterns": AdvisorType.ARCHITECTURE,
    "refactor": AdvisorType.ARCHITECTURE,
    "breaking": AdvisorType.ARCHITECTURE,

    "testing": AdvisorType.RELIABILITY,
    "reliability": AdvisorType.RELIABILITY,
    "fault": AdvisorType.RELIABILITY,
    "recovery": AdvisorType.RELIABILITY,
    "resilience": AdvisorType.RELIABILITY,

    "integration": AdvisorType.INTEGRATION,
    "api": AdvisorType.INTEGRATION,
    "webhook": AdvisorType.INTEGRATION,
    "data pipeline": AdvisorType.INTEGRATION,

    "infrastructure": AdvisorType.DEVOPS,
    "deployment": AdvisorType.DEVOPS,
    "devops": AdvisorType.DEVOPS,
    "ci/cd": AdvisorType.DEVOPS,
    "ops": AdvisorType.DEVOPS,

    "data": AdvisorType.DATA,
    "database": AdvisorType.DATA,
    "migration": AdvisorType.DATA,
    "analytics": AdvisorType.DATA,
}


def route_task_to_advisor(task: dict) -> AdvisorTypeMatch:
    """
    Route a task to the most appropriate advisor type.

    Examines task title, description, layer, and keywords
    to determine which specialized advisor should handle it.

    Args:
        task: Task dict with title, description, layer, required_skills

    Returns:
        AdvisorTypeMatch with primary type, alternatives, confidence, and reason
    """
    title = task.get("title", "").lower()
    description = task.get("description", "").lower()
    layer = task.get("layer", "").lower()
    skills = [s.lower() for s in task.get("required_skills", [])]

    full_text = f"{title} {description} {layer} {' '.join(skills)}"

    # Score each advisor type
    type_scores = {}

    for advisor_type in AdvisorType:
        score = _score_advisor_type(advisor_type, full_text, layer, skills)
        if score > 0:
            type_scores[advisor_type] = score

    # Determine primary and alternative types
    if not type_scores:
        return AdvisorTypeMatch(
            primary_type=AdvisorType.GENERAL,
            alternative_types=[],
            confidence=0.5,
            reason="No specialized domain detected, routing to general advisor"
        )

    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
    primary_type = sorted_types[0][0]
    primary_score = sorted_types[0][1]

    alternatives = [t for t, _ in sorted_types[1:3]]
    confidence = min(primary_score / 100.0, 1.0)  # Normalize to 0-1

    reason = f"Domain analysis: {primary_type.value} advisor selected based on keywords in task description"

    return AdvisorTypeMatch(
        primary_type=primary_type,
        alternative_types=alternatives,
        confidence=confidence,
        reason=reason
    )


def _score_advisor_type(advisor_type: AdvisorType, text: str, layer: str, skills: List[str]) -> float:
    """Score how well an advisor type matches the task"""
    score = 0.0

    # Define keywords for each advisor type
    advisor_keywords = {
        AdvisorType.SECURITY: ["security", "auth", "permission", "encrypt", "vulnerab", "secret", "credential"],
        AdvisorType.PERFORMANCE: ["perform", "optim", "scaling", "bottleneck", "profil", "latency", "throughput"],
        AdvisorType.ARCHITECTURE: ["architect", "design", "pattern", "refactor", "breaking", "redesign", "system"],
        AdvisorType.RELIABILITY: ["test", "reliab", "fault", "recovery", "resilient", "robust", "failure"],
        AdvisorType.INTEGRATION: ["integration", "api", "webhook", "pipeline", "connect"],
        AdvisorType.DEVOPS: ["infrastructure", "deploy", "devops", "ci/cd", "ops", "docker", "kubernetes"],
        AdvisorType.DATA: ["data", "database", "migration", "analytics", "schema", "sql"],
    }

    keywords = advisor_keywords.get(advisor_type, [])

    # Score based on keyword matches
    for keyword in keywords:
        if keyword in text:
            score += 10  # 10 points per keyword match

    # Bonus for exact layer match
    if layer and advisor_type.value in [layer.lower()]:
        score += 20

    # Bonus for skill matches
    for skill in skills:
        if any(kw in skill for kw in keywords):
            score += 15

    return score


def select_advisor_for_task(task: dict) -> dict:
    """
    Select the best advisor for a task and populate advisor metadata.

    Args:
        task: Task dict

    Returns:
        Updated task dict with advisor_type and advisor_routing metadata
    """
    match = route_task_to_advisor(task)

    task['advisor_type'] = match.primary_type.value
    task['advisor_routing'] = {
        'primary_type': match.primary_type.value,
        'alternative_types': [t.value for t in match.alternative_types],
        'confidence': match.confidence,
        'reason': match.reason,
    }

    return task


if __name__ == "__main__":
    # Test routing with sample tasks
    test_tasks = [
        {
            "title": "Add SQL injection prevention",
            "description": "Implement parameterized queries in user API",
            "layer": "security",
            "required_skills": ["security-review"]
        },
        {
            "title": "Optimize dashboard queries",
            "description": "Profile and reduce N+1 queries",
            "layer": "backend",
            "required_skills": ["performance-tuning"]
        },
        {
            "title": "Redesign auth system",
            "description": "Move from session-based to JWT",
            "layer": "infrastructure",
            "required_skills": ["architecture-review", "security"]
        },
    ]

    print("=" * 70)
    print("ADVISOR TYPE ROUTING TEST")
    print("=" * 70)

    for task in test_tasks:
        match = route_task_to_advisor(task)
        print(f"\nTask: {task['title']}")
        print(f"  Primary: {match.primary_type.value} (confidence: {match.confidence:.2f})")
        print(f"  Alternatives: {[t.value for t in match.alternative_types]}")
        print(f"  Reason: {match.reason}")

    print("\n✓ Advisor type routing working")
