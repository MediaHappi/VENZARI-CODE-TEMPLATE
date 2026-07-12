#!/usr/bin/env python3
"""
Skill loader for YOUR-AI agents — unified index of all available skills.

Scans skill directories:
  1. agents/skills/                          — Your-AI-specific workflow skills (PRIMARY)
  2. agents/operators/                       — Meta-skills (operators, NEW)
  3. agents/vendors/agent-skills/skills/     — Addyosmani/agent-skills (REFERENCE)
  4. agents/vendors/mattpocock-skills/skills/ — Mattpocock skills (REFERENCE, recursive)
  5. agents/vendors/ruflo-skills/            — ruvnet/ruflo AI orchestration (38 skills)
  6. agents/vendors/n8n-skills/              — czlonkowski/n8n-skills (7 skills)
  7. agents/vendors/zebbern-security/        — zebbern security/pentest (29 skills)
  8. agents/vendors/trailofbits-skills/      — Trail of Bits security (73 skills, deep)
  9. agents/vendors/anthropics/              — Official Anthropic format reference (NEW)
 10. agents/vendors/alirezarezvani/          — Multi-domain platform operations (NEW, 15 skills)
 11. agents/vendors/aman-bhandari/           — Rule obsolescence (NEW)
 12. agents/vendors/levnikolaevich/          — Hash-verified editing (NEW)

Usage:
  python3 skill_loader.py list                 — print all skills (name + purpose)
  python3 skill_loader.py load <skill-name>    — print full SKILL.md content
  python3 skill_loader.py find <keyword>       — search skills by keyword
  python3 skill_loader.py count               — print total skill count
  python3 skill_loader.py validate <name>      — check skill format compliance (NEW)

Skill loading follows claude-code-harness s07 pattern:
  Layer 1 (cheap): skill names + one-line descriptions in SYSTEM prompt
  Layer 2 (on-demand): full SKILL.md loaded when the agent needs it
"""
import sys, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from incident_detector import Incident, IncidentType, IncidentSeverity
from finding_creator import FindingCreator
from opensre_findings_format import OpenSREFindingsExporter

REPO_ROOT = Path(os.environ.get("PROJECT_CTO_PATH", "/opt/YOUR-PROJECT"))


def export_skill_loading_finding(skill_name: str, source: str, success: bool):
    """REAL: Export skill loading events to findings"""
    try:
        finding_creator = FindingCreator()
        findings_exporter = OpenSREFindingsExporter()

        incident = Incident(
            id=f"incident-skill-load-{hash(skill_name) % 1000000}-{int(datetime.now().timestamp())}",
            service="skill-loader",
            incident_type=IncidentType.OPERATIONAL_ISSUE,
            severity=IncidentSeverity.INFORMATIONAL,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title=f"Skill loaded: {skill_name} from {source}",
            evidence=[{"type": "skill_load", "text": f"Skill: {skill_name}, Source: {source}, Success: {success}"}],
            related_metrics={"skill": skill_name, "source": source}
        )

        finding = finding_creator.create_finding_from_incident(incident)
        findings_exporter.export_finding(finding)
    except Exception:
        pass  # Non-blocking


# (path, source, scan_mode)
# scan_mode: "flat" = direct children, "recursive" = two-level (mattpocock), "deep" = find all SKILL.md
SKILL_DIRS = [
    (REPO_ROOT / "agents/skills",                              "jeanne",       "flat"),
    (REPO_ROOT / "agents/vendors/agent-skills/skills",         "agent-skills", "flat"),
    (REPO_ROOT / "agents/vendors/mattpocock-skills/skills",    "mattpocock",   "recursive"),
    (REPO_ROOT / "agents/vendors/ruflo-skills",                "ruflo",        "flat"),
    (REPO_ROOT / "agents/vendors/n8n-skills",                  "n8n-skills",   "flat"),
    (REPO_ROOT / "agents/vendors/zebbern-security",            "zebbern",      "flat"),
    (REPO_ROOT / "agents/vendors/trailofbits-skills",          "trailofbits",  "deep"),
    # New vendor sources (2026-05-30)
    (REPO_ROOT / "agents/vendors/anthropics",                  "anthropics",   "flat"),
    (REPO_ROOT / "agents/vendors/alirezarezvani",              "alirezarezvani","flat"),
    (REPO_ROOT / "agents/vendors/aman-bhandari",               "aman-bhandari","flat"),
    (REPO_ROOT / "agents/vendors/levnikolaevich",              "levnikolaevich","flat"),
    # Operators (meta-skills)
    (REPO_ROOT / "agents/operators",                           "operators",    "flat"),
]

# Mattpocock subdirectory categories to include (skip deprecated)
MATTPOCOCK_INCLUDE = {"engineering", "productivity", "misc", "personal", "in-progress"}

SKILL_REGISTRY: dict[str, dict] = {}

# Task 1649: Support loading from agents/SKILL_REGISTRY.md (metadata format)
def _load_from_registry_md():
    """Load skill metadata from agents/SKILL_REGISTRY.md if available."""
    registry_path = REPO_ROOT / "agents" / "SKILL_REGISTRY.md"
    if not registry_path.exists():
        return {}

    registry = {}
    try:
        content = registry_path.read_text()
        # Parse table rows: | name | source | scopes | description |
        in_table = False
        for line in content.split('\n'):
            if '| Name |' in line or '| name |' in line:
                in_table = True
                continue
            if in_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 4 and parts[0] and not parts[0].startswith('---'):
                    name, source, scopes, desc = parts[0], parts[1], parts[2], parts[3]
                    scopes_list = [s.strip() for s in scopes.split(',')]
                    registry[name] = {
                        "name": name,
                        "source": source,
                        "scopes": scopes_list,
                        "description": desc[:100],
                    }
    except Exception:
        pass  # Fall back to scanning if registry parsing fails

    return registry

def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line and not line.startswith("---"):
            return line
    return ""

def _register(entry: Path, source: str, category: str = "") -> None:
    manifest = entry / "SKILL.md"
    if not manifest.exists():
        manifest = entry / "skill.md"
    if not manifest.exists():
        return
    raw = manifest.read_text(encoding="utf-8", errors="replace")
    description = _first_line(raw)
    name = entry.name
    if source == "jeanne":
        key = name
    elif category:
        key = f"{source}/{category}/{name}"
    else:
        key = f"{source}/{name}"
    SKILL_REGISTRY[key] = {
        "name": name,
        "key": key,
        "source": source,
        "category": category,
        "description": description[:100],
        "path": str(manifest),
        "content": raw,
    }

def _scan():
    for skill_dir, source, scan_mode in SKILL_DIRS:
        if not skill_dir.exists():
            continue
        if scan_mode == "flat":
            for entry in sorted(skill_dir.iterdir()):
                if entry.is_dir():
                    _register(entry, source)
        elif scan_mode == "recursive":
            # Two-level: category → skill (mattpocock pattern)
            for category_dir in sorted(skill_dir.iterdir()):
                if not category_dir.is_dir():
                    continue
                if category_dir.name not in MATTPOCOCK_INCLUDE:
                    continue
                for skill_entry in sorted(category_dir.iterdir()):
                    if skill_entry.is_dir():
                        _register(skill_entry, source, category=category_dir.name)
        elif scan_mode == "deep":
            # Deep: find all SKILL.md files at any depth, use parent dir as skill entry
            for manifest in sorted(skill_dir.rglob("SKILL.md")):
                _register(manifest.parent, source)

# Task 1649: Load from registry if available; fall back to scanning
_registry_skills = _load_from_registry_md()
if _registry_skills:
    # Update SKILL_REGISTRY from metadata (lightweight)
    for name, meta in _registry_skills.items():
        SKILL_REGISTRY[name] = {
            "name": name,
            "key": name,
            "source": meta.get("source", "unknown"),
            "category": "",
            "description": meta.get("description", ""),
            "scopes": meta.get("scopes", []),
            "path": "",
            "content": "",
        }
else:
    # Fall back to scanning if registry unavailable
    _scan()

def list_skills():
    if not SKILL_REGISTRY:
        print("(no skills found)")
        return
    by_source: dict[str, dict] = {}
    for k, v in SKILL_REGISTRY.items():
        src = v["source"]
        by_source.setdefault(src, {})[k] = v

    source_order = [
        "jeanne", "operators",
        "agent-skills", "mattpocock", "ruflo", "n8n-skills", "zebbern", "trailofbits",
        "anthropics", "alirezarezvani", "aman-bhandari", "levnikolaevich",
    ]
    source_labels = {
        "jeanne":           "YOUR-AI Workflow Skills (PRIMARY)",
        "operators":        "YOUR-AI Operators (meta-skills, NEW)",
        "agent-skills":     "Agent-Skills Vendor (addyosmani)",
        "mattpocock":       "Mattpocock Skills",
        "ruflo":            "Ruflo AI Orchestration (ruvnet)",
        "n8n-skills":       "n8n Skills (czlonkowski)",
        "zebbern":          "Zebbern Security/Pentest",
        "trailofbits":      "Trail of Bits Security (trailofbits)",
        "anthropics":       "Anthropic Official Skills (canonical format)",
        "alirezarezvani":   "alirezarezvani/claude-skills (platform operations)",
        "aman-bhandari":    "aman-bhandari/claude-code-agent-skills-framework",
        "levnikolaevich":   "levnikolaevich/claude-code-skills (hash-verified editing)",
    }

    for src in source_order:
        skills = by_source.get(src, {})
        if not skills:
            continue
        label = source_labels.get(src, src)
        print(f"=== {label} ({len(skills)} skills) ===")
        if src == "mattpocock":
            cur_cat = None
            for k, v in skills.items():
                cat = v.get("category", "")
                if cat != cur_cat:
                    print(f"  [{cat}]")
                    cur_cat = cat
                print(f"    {v['name']:<36} — {v['description']}")
        else:
            for k, v in skills.items():
                print(f"  {k:<48} — {v['description']}")
        print()
    print(f"Total: {len(SKILL_REGISTRY)} skills loaded")

def load_skill(name: str, agent_id: str = "agent", task_id: str = ""):
    import time
    # Try exact key first, then search by name
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        matches = [v for v in SKILL_REGISTRY.values() if v["name"] == name]
        if matches:
            skill = matches[0]  # prefer jeanne source (scanned first)
    if not skill:
        # Audit the failed load (Task 1834)
        try:
            from ops.agent.skill_audit import log_skill_load
            log_skill_load(name, duration_ms=0, success=False, agent_id=agent_id,
                           task_id=task_id, error="skill_not_found")
        except Exception:
            pass
        print(f"Skill not found: '{name}'")
        print("Run 'skill_loader.py list' to see all skills.")
        sys.exit(1)

    t0 = time.monotonic()
    content = skill["content"]
    duration_ms = (time.monotonic() - t0) * 1000
    version = ""
    try:
        import re
        fm = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if fm:
            ver_match = re.search(r'^version:\s*(.+)$', fm.group(1), re.MULTILINE)
            if ver_match:
                version = ver_match.group(1).strip()
    except Exception:
        pass

    # Audit successful load (Task 1834)
    try:
        from ops.agent.skill_audit import log_skill_load
        log_skill_load(name, duration_ms=duration_ms, success=True, agent_id=agent_id,
                       task_id=task_id, version=version)
    except Exception:
        pass

    print(f"# Skill: {skill['key']} (source: {skill['source']})")
    print(f"# Path: {skill['path']}")
    print()
    print(content)

def find_skills(keyword: str):
    keyword = keyword.lower()
    matches = [
        v for v in SKILL_REGISTRY.values()
        if keyword in v["name"].lower() or keyword in v["description"].lower() or keyword in v["content"].lower()
    ]
    if not matches:
        print(f"(no skills match '{keyword}')")
        return
    for v in matches:
        print(f"  {v['key']:<40} — {v['description']}")

def catalog_for_system_prompt() -> str:
    """Return a compact skill catalog suitable for injecting into an agent SYSTEM prompt."""
    lines = []
    jeanne = {k: v for k, v in SKILL_REGISTRY.items() if v["source"] == "jeanne"}
    for k, v in jeanne.items():
        lines.append(f"- **{k}**: {v['description']}")
    return "\n".join(lines)

def validate_skill(name: str) -> bool:
    """Validate a skill's format compliance against the hybrid template spec."""
    _scan()
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        print(f"ERROR: Skill '{name}' not found")
        return False

    content = skill.get("content", "")
    errors = []
    warnings = []

    # Critical checks (blocks skill loading)
    if not content.startswith("---"):
        errors.append("Missing YAML frontmatter (must start with ---)")
    else:
        import re
        fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            if "name:" not in fm:
                errors.append("Frontmatter missing 'name:' field")
            if "description:" not in fm:
                errors.append("Frontmatter missing 'description:' field")
            if "version:" not in fm:
                warnings.append("Frontmatter missing 'version:' field (recommended)")
            if "compatible-roles:" not in fm:
                warnings.append("Frontmatter missing 'compatible-roles:' field (recommended)")

    # Major checks (degrades effectiveness)
    if "## Brief" not in content:
        warnings.append("Missing '## Brief' section (hybrid format requires Brief/Detail/Reference)")
    if "## Detail" not in content:
        warnings.append("Missing '## Detail' section")
    if "## Reference" not in content:
        warnings.append("Missing '## Reference' section")

    line_count = len(content.split('\n'))
    if line_count > 400:
        warnings.append(f"Skill is {line_count} lines (recommended: under 400)")

    if errors:
        print(f"FAIL: {name} — {len(errors)} error(s), {len(warnings)} warning(s)")
        for e in errors:
            print(f"  ERROR: {e}")
        for w in warnings:
            print(f"  WARN:  {w}")
        return False
    else:
        print(f"OK: {name} — 0 errors, {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  WARN: {w}")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: skill_loader.py <list|load|find|count|validate> [arg]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_skills()
    elif cmd == "count":
        _scan()
        print(len(SKILL_REGISTRY))
    elif cmd == "load" and len(sys.argv) >= 3:
        load_skill(sys.argv[2])
    elif cmd == "find" and len(sys.argv) >= 3:
        find_skills(sys.argv[2])
    elif cmd == "validate" and len(sys.argv) >= 3:
        ok = validate_skill(sys.argv[2])
        sys.exit(0 if ok else 1)
    else:
        print(f"Unknown command '{cmd}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
