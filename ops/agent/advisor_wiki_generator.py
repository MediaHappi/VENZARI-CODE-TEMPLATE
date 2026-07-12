#!/usr/bin/env python3
"""
Advisor Wiki Generator — Auto-generate wiki articles from advisor findings

When an advisor completes, automatically create a wiki article documenting:
- The advisor's analysis and recommendations
- Related tasks that used these findings
- Links to knowledge base entries
- Decision history

This ensures all advisor work is permanently documented and searchable.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
import sys

# Overridable via PROJECT_CTO_PATH for test isolation (2026-07-02) — matches
# advisor_manager.py's pattern. A FUNCTION, not a module-level constant: a
# constant freezes at first import, so setting the env var later in the same
# process would silently have no effect.
def _repo_dir() -> Path:
    return Path(os.environ.get('PROJECT_CTO_PATH', '/opt/YOUR-PROJECT'))


def generate_advisor_wiki(advisor_id, advisor_data, findings, evidence):
    """
    Generate a wiki article from completed advisor findings.

    Args:
        advisor_id: The advisor ID (e.g., "ADV0000000001")
        advisor_data: Full advisor dict with metadata
        findings: The findings dict
        evidence: Evidence string

    Returns:
        Path to generated wiki file
    """
    wiki_dir = _repo_dir() / 'docs' / 'wiki'
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # Create article slug from advisor title
    title = advisor_data.get('title', 'Unknown')
    slug = title.lower().replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')[:50]

    filename = wiki_dir / f"advisor-{advisor_id}-{slug}.md"

    # Human-readable title: strip the redundant "Task Review: " / "Approval Review: "
    # prefix advisor titles carry (the article's own header already establishes it's a
    # wiki entry) so the heading reads like a sentence, not a log line.
    display_title = title
    for prefix in ("Task Review: ", "Approval Review: "):
        if display_title.startswith(prefix):
            display_title = display_title[len(prefix):]
            break

    # One-sentence, plain-English summary — prefer findings.plan_summary (deterministic
    # reviews always set this), fall back to the raw evidence string, then a generic line.
    one_liner = None
    if isinstance(findings, dict):
        one_liner = findings.get('plan_summary') or findings.get('summary')
    if not one_liner:
        one_liner = (evidence or "").strip().split("\n")[0][:300] or "No summary available."

    domain = advisor_data.get('domain', 'general')

    # WIKI ARTICLE template (task E0000000010, docs/governance/DOC-TEMPLATE-SYSTEM.md):
    # frontmatter + human-readable title + one-sentence plain-English summary + short
    # "What happened" prose BEFORE any structured/technical detail. Billy's direct
    # feedback on the old format: "It is absolutely terrible. It's probably easy for you
    # to read. I can't read it at all." — the fix is ordering, not deleting detail: every
    # field the old template had is still here, just after the human-readable part, not
    # instead of it.
    article = f"""---
doc_type: wiki
generated_at: {datetime.now(timezone.utc).isoformat()}
source_task: {advisor_id}
---
# {display_title}

**In one sentence:** {one_liner}

## What happened

Advisor `{advisor_id}` reviewed this in the **{domain}** domain and completed with status
**{advisor_data.get('status', 'completed')}**. Full technical findings and evidence are
below, but the short version is the one-sentence summary above.

## Details

### Analysis & Findings

{format_findings(findings)}

### Evidence

```
{evidence}
```

### Closing Skills

Skills used to validate/implement findings:
{chr(10).join(f"- `{skill}`" for skill in advisor_data.get('closing_skills', []))}

### Knowledge Base Integration

This advisor's findings have been persisted to:
- `.team/knowledge/{domain}/finding-{advisor_id}.json`
- Available for injection into future tasks in this domain

### Reference Commands

Future tasks and sessions can retrieve this analysis with:

```bash
# Full advisor record (status, findings, evidence)
python3 /opt/YOUR-PROJECT/ops/agent/advisor_manager.py status {advisor_id}

# All findings for this domain (injected into task claims automatically)
python3 /opt/YOUR-PROJECT/ops/agent/advisor_manager.py get-findings {domain}

# Raw knowledge-base entry
cat /opt/YOUR-PROJECT/.team/knowledge/{domain}/finding-{advisor_id}.json
```

### Related References

- [Advisor Manager](/docs/ADVISOR_MANAGER.md)
- [{domain.title()} Layer Runbook](/docs/RUNBOOKS.md)

---

*Auto-generated wiki article. See advisor_wiki_generator.py for generation logic.*
"""

    with open(filename, 'w') as f:
        f.write(article)

    return filename


def format_findings(findings):
    """Format findings dict as markdown."""
    if not findings:
        return "(No findings provided)"

    parts = []

    if isinstance(findings, dict):
        for key, value in findings.items():
            if isinstance(value, list):
                parts.append(f"### {key.replace('_', ' ').title()}")
                for item in value:
                    parts.append(f"- {item}")
                parts.append("")
            elif isinstance(value, dict):
                parts.append(f"### {key.replace('_', ' ').title()}")
                for k, v in value.items():
                    parts.append(f"- **{k}:** {v}")
                parts.append("")
            else:
                parts.append(f"### {key.replace('_', ' ').title()}")
                parts.append(f"{value}")
                parts.append("")

    return "\n".join(parts)


def update_wiki_index(advisor_id, advisor_title, domain):
    """Update wiki index to link to advisor article."""
    index_file = _repo_dir() / 'docs' / 'wiki' / 'INDEX.md'

    # Ensure index exists
    if not index_file.exists():
        with open(index_file, 'w') as f:
            f.write("# Wiki Index\n\n## Advisors\n\n")

    # Read current index
    with open(index_file, 'r') as f:
        content = f.read()

    # Check if advisor already linked
    if advisor_id in content:
        return  # Already indexed

    # Add advisor to index
    slug = advisor_title.lower().replace(' ', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')[:50]
    link = f"- [{advisor_title}](advisor-{advisor_id}-{slug}.md) ({domain})\n"

    # Find Advisors section and add under domain
    lines = content.split('\n')
    new_lines = []
    in_advisors = False
    inserted = False

    for line in lines:
        new_lines.append(line)
        if line.startswith('## Advisors'):
            in_advisors = True
        elif in_advisors and not inserted and line.startswith('##'):
            # Hit next section without inserting
            new_lines.insert(-1, link)
            inserted = True
            in_advisors = False

    if in_advisors and not inserted:
        new_lines.append(link)

    # Write updated index
    with open(index_file, 'w') as f:
        f.write('\n'.join(new_lines))


if __name__ == "__main__":
    # Test
    test_advisor = {
        "id": "ADV0000000001",
        "title": "Memory Optimization Analysis",
        "domain": "infrastructure",
        "closing_skills": ["memory-optimization", "architecture-review"],
    }
    test_findings = {
        "analysis": "Memory leak detected",
        "recommendations": [
            "Implement weak references",
            "Add TTL limits",
        ]
    }
    test_evidence = "512MB → 2.1GB over 24h"

    wiki_file = generate_advisor_wiki(
        "ADV0000000001",
        test_advisor,
        test_findings,
        test_evidence
    )
    print(f"✓ Wiki generated: {wiki_file}")
    update_wiki_index("ADV0000000001", "Memory Optimization Analysis", "infrastructure")
    print(f"✓ Wiki index updated")
