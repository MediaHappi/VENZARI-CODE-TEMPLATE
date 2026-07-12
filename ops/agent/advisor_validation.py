#!/usr/bin/env python3
"""
Advisor Findings Validator - Closes the feedback loop

Validates advisor recommendations against actual task completion outcomes.
Tracks advisor accuracy and identifies pattern misses.

This is CRITICAL: Advisor quality never improves without feedback.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))


def validate_advisor_findings(
    task_id: str,
    advisor_findings: Dict,
    actual_evidence: str,
    completion_summary: str,
    skill_used: str
) -> Dict:
    """
    Validate advisor findings against actual completion outcome.

    Returns validation report with:
    - accuracy_score (0-100)
    - findings_match (bool)
    - missed_issues (list of issues advisor didn't identify)
    - over_predicted (list of issues advisor found that didn't matter)
    """

    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'task_id': task_id,
        'advisor_findings': advisor_findings.get('plan', ''),
        'actual_evidence': actual_evidence,
        'skill_used': skill_used,
        'validation_results': {
            'accuracy_score': 0,
            'findings_matched': False,
            'missed_critical_issues': [],
            'over_predicted': [],
            'evidence_alignment': False,
            'recommendations_applicable': False
        }
    }

    # Analyze alignment
    findings_text = str(advisor_findings).lower()
    evidence_text = (actual_evidence or '').lower()
    summary_text = (completion_summary or '').lower()

    # Check if advisor's plan aligns with actual evidence
    alignment_score = 0

    # Keywords that indicate good prediction
    good_keywords = ['pass', 'verify', 'tested', 'success', 'confirmed', 'working']
    for keyword in good_keywords:
        if keyword in evidence_text:
            alignment_score += 10

    # Keywords that indicate missed issues
    missed_keywords = ['failed', 'error', 'broken', 'incomplete', 'missing']
    for keyword in missed_keywords:
        if keyword in evidence_text and keyword not in findings_text:
            report['validation_results']['missed_critical_issues'].append(keyword)

    # Cap score at 100
    report['validation_results']['accuracy_score'] = min(alignment_score, 100)
    report['validation_results']['findings_matched'] = alignment_score > 50
    report['validation_results']['evidence_alignment'] = alignment_score > 70

    return report


def persist_validation_report(task_id: str, report: Dict) -> Path:
    """Save validation report to knowledge base."""
    kb_dir = Path('/opt/YOUR-PROJECT/.team/knowledge/advisor-validation')
    kb_dir.mkdir(parents=True, exist_ok=True)

    report_file = kb_dir / f"validation_{task_id}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    return report_file


def get_advisor_accuracy_metrics(domain: str = None) -> Dict:
    """Calculate advisor accuracy across all completed tasks."""
    kb_dir = Path('/opt/YOUR-PROJECT/.team/knowledge/advisor-validation')

    if not kb_dir.exists():
        return {'status': 'no_data', 'total_validations': 0}

    validations = []
    for report_file in kb_dir.glob('validation_*.json'):
        try:
            with open(report_file) as f:
                report = json.load(f)
                validations.append(report)
        except:
            pass

    if not validations:
        return {'status': 'no_data', 'total_validations': 0}

    total = len(validations)
    accurate = sum(1 for v in validations if v['validation_results']['evidence_alignment'])
    avg_score = sum(v['validation_results']['accuracy_score'] for v in validations) / total

    return {
        'total_validations': total,
        'accurate_predictions': accurate,
        'accuracy_percentage': (accurate / total * 100) if total > 0 else 0,
        'average_score': avg_score,
        'missed_issues_count': sum(
            len(v['validation_results']['missed_critical_issues'])
            for v in validations
        )
    }


if __name__ == "__main__":
    # Test validation
    test_findings = {'plan': 'Test plan', 'recommendation': 'PROCEED'}
    test_evidence = 'Test passed, curl → HTTP 200, all gates passed'

    report = validate_advisor_findings(
        task_id='TEST-001',
        advisor_findings=test_findings,
        actual_evidence=test_evidence,
        completion_summary='Task completed successfully',
        skill_used='testing'
    )

    print(json.dumps(report, indent=2))
