#!/usr/bin/env python3
"""
Advisor Manager — Persistent Advisor State Management (Task 10003)

Similar to task_manager.py, but for advisor work.
Manages advisor lifecycle: create → claim → complete
Persists findings for reuse across similar tasks.

Usage:
  python3 advisor_manager.py list                    # show all advisors
  python3 advisor_manager.py create TITLE DOMAIN SKILLS -- domain: infrastructure|testing|memory|etc
  python3 advisor_manager.py claim ADVISOR_ID ROLE   # claim an advisor for work
  python3 advisor_manager.py complete ADVISOR_ID FINDINGS EVIDENCE --skill SKILL
  python3 advisor_manager.py get-findings DOMAIN     # retrieve findings for domain

Schema (advisor-{id}.json):
  id, title, domain, required_skills, closing_skills, status (pending/in_progress/completed),
  findings (dict), evidence (str), claimed_at, completed_at, failure_count, created_at
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import re

# Overridable via PROJECT_CTO_PATH so tests can point advisor state at a temp dir
# instead of writing real .advisors/.team/knowledge/.memory_archive/docs/wiki
# records into production on every test run (2026-07-02 — matches the pattern
# approval_gate.py already used for REPO_DIR). These are FUNCTIONS, not
# module-level constants: a constant would freeze at first import, so setting
# the env var later in the same process (e.g. mid pytest session, after some
# other test already imported this module) would silently have no effect.
def _repo_dir() -> Path:
    return Path(os.environ.get('PROJECT_CTO_PATH', '/opt/YOUR-PROJECT'))

def _advisors_dir() -> Path:
    d = _repo_dir() / '.advisors'
    d.mkdir(parents=True, exist_ok=True)
    return d

def _knowledge_dir() -> Path:
    d = _repo_dir() / '.team' / 'knowledge'
    d.mkdir(parents=True, exist_ok=True)
    return d

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def get_next_advisor_id():
    """Generate next advisor ID using ADV + 10 digit format."""
    existing = [f.stem for f in _advisors_dir().glob('ADV*.json')]
    nums = []
    for e in existing:
        try:
            m = re.match(r'ADV(\d+)', e)
            if m:
                nums.append(int(m.group(1)))
        except:
            pass
    return f"ADV{(max(nums) + 1) if nums else 1:010d}"

def load_advisor(advisor_id):
    """Load advisor JSON file."""
    f = _advisors_dir() / f"{advisor_id}.json"
    if f.exists():
        return json.load(open(f))
    return None

def save_advisor(advisor_id, advisor):
    """Save advisor JSON file."""
    f = _advisors_dir() / f"{advisor_id}.json"
    with open(f, 'w') as fp:
        json.dump(advisor, fp, indent=2)

def list_advisors(status=None):
    """List all advisors, optionally filtered by status."""
    advisors = []
    for f in sorted(_advisors_dir().glob('ADV*.json')):
        advisor = json.load(open(f))
        if status is None or advisor.get('status') == status:
            advisors.append(advisor)
    return advisors

def create_advisor(title, domain, required_skills, task_context=None):
    """
    Create a new advisor with optional type routing (Task I0000000029).

    Args:
        title: Advisor title
        domain: Domain (layer) for classification
        required_skills: List of required skills
        task_context: Optional task dict for advisor type routing

    Returns:
        advisor ID
    """
    advisor_id = get_next_advisor_id()

    if not domain:
        domain = 'infrastructure'

    # Determine advisor type via routing (Task I0000000029)
    advisor_type = 'general'
    advisor_routing = None
    if task_context:
        try:
            from advisor_type_router import route_task_to_advisor
            match = route_task_to_advisor(task_context)
            advisor_type = match.primary_type.value
            advisor_routing = {
                'primary_type': match.primary_type.value,
                'alternative_types': [t.value for t in match.alternative_types],
                'confidence': match.confidence,
                'reason': match.reason,
            }
        except ImportError:
            pass  # Router not available — use general

    # Determine default closing_skills based on domain
    default_closing_skills = {
        'infrastructure': ['infrastructure', 'build-and-verify'],
        'backend': ['backend', 'testing'],
        'testing': ['testing', 'infrastructure'],
        'memory': ['memory', 'architecture-review'],
        'security': ['security-review', 'code-review-and-quality'],
        'documentation': ['documentation', 'task-completion-verifier'],
        'frontend': ['frontend', 'code-review-and-quality'],
        'devops': ['devops', 'infrastructure'],
    }

    advisor = {
        'id': advisor_id,
        'title': title,
        'domain': domain,
        'advisor_type': advisor_type,
        'required_skills': required_skills if isinstance(required_skills, list) else [required_skills],
        'closing_skills': default_closing_skills.get(domain, ['infrastructure', 'code-review-and-quality']),
        'status': 'pending',
        'assigned_to': None,
        'findings': None,
        'evidence': None,
        'claimed_at': None,
        'completed_at': None,
        'failure_count': 0,
        'created_at': utcnow(),
    }

    if advisor_routing:
        advisor['advisor_routing'] = advisor_routing

    save_advisor(advisor_id, advisor)
    print(f"Created advisor {advisor_id}: {title} (type: {advisor_type})")
    return advisor_id

def get_skills_for_domain(title: str, domain: str) -> list:
    """Wire skill_matcher to get domain-specific skills."""
    try:
        from skill_matcher import recommend_skills
        return recommend_skills(f"{domain}: {title}", role=domain, top_n=5)
    except:
        return []


DEFAULT_MODEL_CHAIN = [
    # 'fable',  # disabled 2026-07-02 — repeated timeouts in live use (Billy), may re-add later
    'opus',
    'sonnet',
]
def _advisor_config_file() -> Path:
    return _repo_dir() / 'ops' / 'agent' / 'advisor_config.json'


def get_model_chain() -> list:
    """Model fallback chain: env ADVISOR_MODEL_CHAIN > advisor_config.json > default fable,opus,sonnet."""
    env_chain = os.environ.get('ADVISOR_MODEL_CHAIN', '').strip()
    if env_chain:
        return [m.strip() for m in env_chain.split(',') if m.strip()]
    if _advisor_config_file().exists():
        try:
            chain = json.load(open(_advisor_config_file())).get('model_chain')
            if chain and isinstance(chain, list):
                return chain
        except Exception as e:
            print(f"  ⚠️  advisor_config.json unreadable ({e}), using default chain", file=sys.stderr)
    return list(DEFAULT_MODEL_CHAIN)


def get_model_timeout() -> int:
    """Per-model timeout in seconds: env ADVISOR_TIMEOUT_SECONDS, default 600 (10 min)."""
    try:
        return int(os.environ.get('ADVISOR_TIMEOUT_SECONDS', '600'))
    except ValueError:
        print(f"  ⚠️  Invalid ADVISOR_TIMEOUT_SECONDS, using 600", file=sys.stderr)
        return 600


def _invoke_single_model(model: str, prompt: str, timeout: int) -> str:
    """
    Invoke one model via claude CLI with file-based I/O.
    Returns raw output text. Raises RuntimeError with full diagnostics on failure.
    On failure the model's actual output is PRINTED, never silently discarded.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        prompt_file = f.name
    output_file = prompt_file.replace('.txt', '.out')

    env = os.environ.copy()

    def _read_output():
        try:
            with open(output_file, 'r') as f:
                return f.read().strip()
        except OSError:
            return ''

    def _cleanup():
        for p in (prompt_file, output_file):
            if os.path.exists(p):
                os.unlink(p)

    try:
        print(f"  → Spawning: claude --model={model} --print (timeout {timeout}s)", file=sys.stderr)
        sys.stderr.flush()

        with open(prompt_file, 'r') as stdin_f, open(output_file, 'w') as stdout_f:
            result = subprocess.run(
                ['claude', f'--model={model}', '--print'],
                stdin=stdin_f,
                stdout=stdout_f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env
            )

        output = _read_output()
        print(f"  ← {model} returned (exit code: {result.returncode}, {len(output)} chars)", file=sys.stderr)
        sys.stderr.flush()

        if result.returncode != 0:
            # Diagnostics: show BOTH streams before failing — never hide the real error
            print(f"  ❌ {model} failed (exit {result.returncode})", file=sys.stderr)
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}", file=sys.stderr)
            if output:
                print(f"  stdout: {output[:500]}", file=sys.stderr)
            _cleanup()
            raise RuntimeError(
                f"{model} invocation failed (exit {result.returncode}): "
                f"stderr={result.stderr[:200] if result.stderr else 'empty'} "
                f"stdout={output[:200] if output else 'empty'}")

        if not output:
            print(f"  ❌ {model} returned empty output", file=sys.stderr)
            _cleanup()
            raise RuntimeError(f"{model} returned no output")

        _cleanup()
        return output

    except subprocess.TimeoutExpired:
        partial = _read_output()
        print(f"  ❌ {model} timeout after {timeout}s", file=sys.stderr)
        if partial:
            print(f"  partial output: {partial[:300]}", file=sys.stderr)
        _cleanup()
        raise RuntimeError(f"{model} analysis timed out (>{timeout}s)")
    except FileNotFoundError:
        print(f"  ❌ claude CLI not found", file=sys.stderr)
        _cleanup()
        raise RuntimeError(f"claude CLI not available. Cannot invoke {model}.")


def build_analysis_prompt(advisor_id: str, title: str, domain: str, required_skills: list, description: str = '') -> str:
    """Build a targeted advisor prompt via the O0000000007 template system (task
    O0000000009: this function used to hardcode one generic "deep architectural audit"
    prompt for every advisor call regardless of what was actually being reviewed --
    O0000000004 (historical completion evidence audit) and O0000000005 (repo-map/context
    architecture review) both need genuinely targeted prompts, not the same fixed
    question set every time.

    Selects a template (historical_verification, repo_map, closing_gate, documentation,
    security, or the task_review fallback) from advisor_prompt_templates.select_template()
    based on the advisor's title/domain, then renders it via render_prompt(). Returned
    findings will follow that template's required output fields (verdict/risks/
    required_fixes/verification_plan/confidence, or template-specific fields like
    sampled_tasks/reopen_tasks for historical_verification) -- the caller
    (complete_advisor()) stores findings generically and only validates substance
    (500+ chars), so this does not require any caller-side schema change.
    """
    from advisor_prompt_templates import select_template, render_prompt

    recommended_skills = get_skills_for_domain(title, domain)
    all_skills = list(set(required_skills or []) | set(recommended_skills))

    synthetic_task = {
        'id': advisor_id,
        'title': title,
        'description': description,
        'layer': domain,
        'required_skills': all_skills,
    }
    template_name = select_template(synthetic_task)

    class _Request:
        pass
    request = _Request()
    request.prompt_template = template_name
    request.task = synthetic_task
    request.requester = 'advisor_manager.invoke_model_for_analysis'
    request.context_files = [f"/opt/YOUR-PROJECT (repo root, domain: {domain})"]

    return render_prompt(request)


def invoke_model_for_analysis(advisor_id: str, title: str, domain: str, required_skills: list) -> dict:
    """
    Invoke the advisor model chain (default: fable → opus → sonnet) via claude CLI.

    Tries each model in order; on failure moves to the next. Raises only when
    ALL models in the chain fail. Returns {'findings', 'model', 'timestamp'}.
    """
    prompt = build_analysis_prompt(advisor_id, title, domain, required_skills)

    model_chain = get_model_chain()
    timeout = get_model_timeout()

    print(f"  🧠 Invoking advisor model chain: {' → '.join(model_chain)}", file=sys.stderr)
    print(f"     Prompt length: {len(prompt)} chars, per-model timeout: {timeout}s", file=sys.stderr)
    sys.stderr.flush()

    errors = []
    for model in model_chain:
        try:
            output = _invoke_single_model(model, prompt, timeout)
        except RuntimeError as e:
            errors.append(f"{model}: {e}")
            print(f"  ↪ Falling back to next model in chain...", file=sys.stderr)
            continue

        # Parse JSON (direct, then regex extraction from surrounding text)
        findings = None
        try:
            findings = json.loads(output)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                try:
                    findings = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

        if findings is None:
            print(f"  ❌ {model} returned invalid JSON. First 300 chars: {output[:300]}", file=sys.stderr)
            errors.append(f"{model}: output was not valid JSON")
            print(f"  ↪ Falling back to next model in chain...", file=sys.stderr)
            continue

        print(f"  ✓ {model} analysis complete - valid JSON", file=sys.stderr)
        sys.stderr.flush()
        return {
            'findings': findings,
            'model': model,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    raise RuntimeError(
        f"All models in chain failed ({' → '.join(model_chain)}). Errors: " + ' | '.join(errors))


# Backward-compatible alias (external callers/tests may still use the old name)
invoke_opus_for_analysis = invoke_model_for_analysis


def claim_advisor(advisor_id, agent_role):
    """Claim an advisor for work."""
    advisor = load_advisor(advisor_id)
    if not advisor:
        print(f"Advisor {advisor_id} not found", file=sys.stderr)
        sys.exit(1)

    if advisor.get('status') != 'pending':
        print(f"Advisor {advisor_id} is not pending (status: {advisor.get('status')})", file=sys.stderr)
        sys.exit(1)

    advisor['status'] = 'in_progress'
    advisor['assigned_to'] = agent_role
    advisor['claimed_at'] = utcnow()
    save_advisor(advisor_id, advisor)
    print(f"Claimed advisor {advisor_id} for {agent_role}")

def complete_advisor(advisor_id, findings=None, evidence=None, closing_skills=None):
    """
    Complete an advisor with REAL findings from Planner Agent analysis.

    CRITICAL: This function invokes the Planner Agent for genuine reasoning.
    The advisor does NOT accept pre-computed findings - it spawns real analysis.

    Flow:
    1. If findings=None, invoke Planner Agent with advisor scope
    2. Planner Agent analyzes repository with full architectural context
    3. Capture Planner's output as findings
    4. Save to wiki and memory
    5. Mark advisor complete

    If findings ARE provided, they must be output from real Planner Agent work
    (verified by substantial length and evidence of deep analysis).
    """
    import subprocess
    import tempfile

    advisor = load_advisor(advisor_id)
    if not advisor:
        print(f"Advisor {advisor_id} not found", file=sys.stderr)
        sys.exit(1)

    if advisor.get('status') != 'in_progress':
        print(f"Advisor {advisor_id} is not in_progress (status: {advisor.get('status')})", file=sys.stderr)
        sys.exit(1)

    # If findings not provided, RUN REPOSITORY SCANNER + INVOKE OPUS
    if findings is None:
        print(f"🔍 Advisor {advisor_id}: Running real analysis...", file=sys.stderr)
        print(f"   Working directory: {os.getcwd()}", file=sys.stderr)
        print(f"   Task: {advisor.get('title')}", file=sys.stderr)

        # STAGE 1: Repository scanner for ground truth
        try:
            from advisor_repository_scanner import perform_full_scan, generate_findings_from_scan

            print(f"  📊 Stage 1: Repository scanner...", file=sys.stderr)
            sys.stderr.flush()
            scan_results = perform_full_scan()
            scan_findings = generate_findings_from_scan(scan_results)
            evidence_parts = [f"Scanner: {scan_results.get('scan_timestamp', 'unknown')}"]

            print(f"  ✓ Scanner complete ({len(str(scan_findings))} chars)", file=sys.stderr)
            sys.stderr.flush()

        except ImportError as e:
            print(f"❌ Repository scanner not available: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ Repository scan failed: {e}", file=sys.stderr)
            sys.exit(1)

        # STAGE 2: Invoke advisor model chain for architectural analysis
        # CRITICAL: Model analysis is MANDATORY for advisors. No silent fallback to scanner-only.
        domain = advisor.get('domain', 'infrastructure')
        title = advisor.get('title', '')
        required_skills = advisor.get('required_skills', [])

        print(f"  🧠 Stage 2: Invoking model chain for architectural analysis (MANDATORY)...", file=sys.stderr)
        model_findings = None
        model_used = None
        try:
            model_result = invoke_model_for_analysis(advisor_id, title, domain, required_skills)
            if model_result and model_result.get('findings'):
                model_findings = model_result.get('findings')
                model_used = model_result.get('model', 'unknown')
                evidence_parts.append(f"Model {model_used}: {model_result.get('timestamp', 'unknown')}")
                print(f"  ✓ {model_used} analysis complete ({len(str(model_findings))} chars)", file=sys.stderr)
            else:
                print(f"  ❌ ADVISOR COMPLETION FAILED: model returned no findings", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"  ❌ ADVISOR COMPLETION FAILED: model chain error: {e}", file=sys.stderr)
            sys.exit(1)

        # Merge findings: model analysis is mandatory, so we always have combined analysis
        findings = {
            'combined_analysis': True,
            'analysis_model': model_used,
            'code_level_findings': scan_findings if isinstance(scan_findings, dict) else {'raw': str(scan_findings)},
            'architectural_findings': model_findings,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        evidence = ' + '.join(evidence_parts)
        print(f"✅ Combined analysis (scanner + {model_used}): {len(str(findings))} chars", file=sys.stderr)

    # VALIDATION: Findings must be substantial (proof of real analysis)
    if isinstance(findings, str):
        findings_text = findings
        try:
            findings_dict = json.loads(findings)
        except:
            findings_dict = {'raw': findings}
    else:
        if not findings:
            print(f"❌ Findings cannot be empty or None.", file=sys.stderr)
            sys.exit(1)
        findings_dict = findings
        findings_text = json.dumps(findings, indent=2)

    # Verify findings are substantive (real analysis should be 500+ chars minimum)
    if len(findings_text) < 500:
        print(f"❌ Advisor findings must be substantive (minimum 500 characters).", file=sys.stderr)
        print(f"   Provided: {len(findings_text)} characters", file=sys.stderr)
        print(f"   This suggests fabricated or shallow analysis.", file=sys.stderr)
        sys.exit(1)

    # Verify evidence is provided (proof of real work)
    if not evidence:
        print(f"❌ Evidence of analysis is required (e.g., 'Planner Agent analysis took X minutes').", file=sys.stderr)
        sys.exit(1)

    # Prepare completion metadata — advisor is NOT marked completed until
    # wiki + memory persistence succeed (structural enforcement, no silent failure).
    completed_at = utcnow()
    domain = advisor.get('domain', 'general')
    closing_skills_list = closing_skills if isinstance(closing_skills, list) else [closing_skills]

    # Persist findings to knowledge base for reuse
    domain_dir = _knowledge_dir() / domain
    domain_dir.mkdir(parents=True, exist_ok=True)

    finding_file = domain_dir / f"finding-{advisor_id}.json"
    finding_entry = {
        'advisor_id': advisor_id,
        'title': advisor.get('title', ''),
        'domain': domain,
        'findings': findings_dict,
        'evidence': evidence,
        'closing_skills': closing_skills_list,
        'completed_at': completed_at,
        'created_at': advisor['created_at'],
    }
    with open(finding_file, 'w') as f:
        json.dump(finding_entry, f, indent=2)
    if not finding_file.exists():
        print(f"❌ Knowledge base write failed: {finding_file}", file=sys.stderr)
        sys.exit(1)

    # Wiki generation — BLOCKING. An advisor without a wiki document is not complete.
    print(f"  📝 Wiki generation...", file=sys.stderr)
    sys.stderr.flush()
    try:
        from advisor_wiki_generator import generate_advisor_wiki, update_wiki_index
        wiki_file = generate_advisor_wiki(advisor_id, advisor, findings_dict, evidence)
        update_wiki_index(advisor_id, advisor.get('title', ''), domain)
        if not Path(wiki_file).exists():
            raise RuntimeError(f"wiki file not on disk after generation: {wiki_file}")
        print(f"  ✓ Wiki article created: {wiki_file}", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        print(f"  ❌ ADVISOR COMPLETION BLOCKED: wiki generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Memory persistence — BLOCKING, verified by read-back.
    print(f"  💾 Memory persistence...", file=sys.stderr)
    sys.stderr.flush()
    try:
        from wire_all_memory_layers import persist_to_all_layers
        advisor_record = {
            'id': advisor_id,
            'title': advisor.get('title', ''),
            'layer': domain,
            'completed_at': completed_at,
            'summary': f"Advisor findings: {findings_text[:200]}",
            'evidence': evidence,
        }
        summary = f"Advisor {advisor_id} ({advisor.get('title', '')}): {findings_text[:300]}"
        mem_results = persist_to_all_layers(advisor_record, evidence, summary)
        for layer_name in ('l1_redis', 'l2_postgres', 'l3_chromadb', 'l4_codegraph', 'l5_git'):
            ok, msg = mem_results[layer_name]
            print(f"    {'✓' if ok else '✗'} {layer_name}: {msg}", file=sys.stderr)
        # Require a durable layer (L2 or L5), not just any layer — same principle as
        # task_manager.py's completion flow (task I0000000044/EG-004, 2026-07-02): a
        # record that only landed in a 24h Redis cache isn't real institutional memory.
        if not mem_results.get('durable_succeeded'):
            raise RuntimeError("no durable memory layer (L2 PostgreSQL or L5 git-archive) accepted the write")
        # Read-back verification: L5 archive record must exist and parse
        archive_file = _repo_dir() / '.memory_archive' / f"{advisor_id}.json"
        if mem_results['l5_git'][0]:
            readback = json.load(open(archive_file))
            if readback.get('task_id') != advisor_id:
                raise RuntimeError(f"L5 read-back mismatch in {archive_file}")
            print(f"  ✓ Memory read-back verified: {archive_file}", file=sys.stderr)
        print(f"  ✓ Memory persistence complete ({mem_results['success_count']}/5 layers)", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        print(f"  ❌ ADVISOR COMPLETION BLOCKED: memory persistence failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Only now — analysis real, wiki on disk, memory verified — mark completed.
    advisor['status'] = 'completed'
    advisor['findings'] = findings_dict
    advisor['evidence'] = evidence
    advisor['closing_skills'] = closing_skills_list
    advisor['completed_at'] = completed_at
    save_advisor(advisor_id, advisor)

    print(f"✅ Completed advisor {advisor_id}", file=sys.stderr)
    print(f"  Findings persisted to .team/knowledge/{domain}/finding-{advisor_id}.json", file=sys.stderr)
    sys.stderr.flush()

    # W0000000002: Auto-persist advisor findings to L3 semantic memory (2026-07-06)
    try:
        import sys as _sys
        import os as _os
        _sys.path.insert(0, str(Path(__file__).parent))
        from importlib import import_module
        _mg = import_module("memory-governance".replace("-", "_")) if False else None
        # Use exec-based import for hyphenated module name
        _mg_path = Path(__file__).parent / "memory-governance.py"
        if _mg_path.exists():
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location("memory_governance", _mg_path)
            _mg = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mg)
            _advisor_task = {
                'id': advisor_id,
                'title': advisor.get('title', f'Advisor {advisor_id}'),
                'layer': domain,
            }
            _summary = f"Advisor {advisor_id} ({domain}): {str(findings_dict)[:200]}"
            _mg.write_task_findings_to_l3(_advisor_task, evidence or '', _summary)
    except Exception as _e:
        print(f"⚠️  L3 advisor persistence failed (non-blocking): {_e}", file=sys.stderr)

def get_advisor_findings(domain):
    """
    Retrieve all findings for a domain.
    Returns list of findings dicts for task reuse.
    """
    domain_dir = _knowledge_dir() / domain
    if not domain_dir.exists():
        return []

    findings = []
    for f in sorted(domain_dir.glob('finding-*.json')):
        try:
            findings.append(json.load(open(f)))
        except:
            pass
    return findings

def export_task_findings_to_kb(task_id, domain, findings_data, evidence, closing_skill):
    """
    Export findings from a completed task to the knowledge base.
    This bridges task_manager.py completion to the KB for future task reuse.

    Args:
        task_id: The task ID that generated these findings
        domain: The domain (layer) for KB organization
        findings_data: Dict of findings from advisor or task completion
        evidence: Evidence from task completion
        closing_skill: Skill used to complete the task
    """
    domain_dir = _knowledge_dir() / domain
    domain_dir.mkdir(parents=True, exist_ok=True)

    finding_file = domain_dir / f"task-{task_id}-finding.json"
    finding_entry = {
        'source': 'task_completion',
        'task_id': task_id,
        'findings': findings_data,
        'evidence': evidence,
        'closing_skill': closing_skill,
        'domain': domain,
        'exported_at': utcnow(),
    }

    with open(finding_file, 'w') as f:
        json.dump(finding_entry, f, indent=2)

    return str(finding_file)

def show_list():
    """Show all advisors."""
    advisors = list_advisors()
    if not advisors:
        print("No advisors found")
        return

    print(f"{'ID':<15} {'STATUS':<12} {'DOMAIN':<15} {'TITLE'}")
    print('-' * 70)
    for a in advisors:
        status = a.get('status', 'unknown')
        domain = a.get('domain', 'general')
        title = a.get('title', 'Unknown')[:40]
        print(f"{a['id']:<15} {status:<12} {domain:<15} {title}")

if __name__ == '__main__':
    args = sys.argv[1:]

    if not args or args[0] == 'list':
        show_list()

    elif args[0] == 'create' and len(args) >= 3:
        title = args[1]
        domain = args[2]
        skills = args[3:] if len(args) > 3 else ['infrastructure']
        create_advisor(title, domain, skills)

    elif args[0] == 'claim' and len(args) >= 3:
        advisor_id = args[1]
        agent_role = args[2]
        claim_advisor(advisor_id, agent_role)

    elif args[0] == 'complete' and len(args) >= 2:
        # Parse: complete ADVISOR_ID [FINDINGS EVIDENCE] [--skills SKILL1,SKILL2]
        # If FINDINGS not provided, Planner Agent is invoked
        advisor_id = args[1]
        findings = None
        evidence = None
        closing_skills = []

        # Parse optional findings and evidence
        if len(args) > 2 and not args[2].startswith('--'):
            findings = args[2]
        if len(args) > 3 and not args[3].startswith('--'):
            evidence = args[3]

        # Parse optional --skills
        for i in range(2, len(args)):
            if args[i] == '--skills' and i + 1 < len(args):
                closing_skills = [s.strip() for s in args[i + 1].split(',')]
                break

        complete_advisor(advisor_id, findings, evidence, closing_skills)

    elif args[0] == 'get-findings' and len(args) >= 2:
        domain = args[1]
        findings = get_advisor_findings(domain)
        if findings:
            print(f"Found {len(findings)} findings for domain '{domain}':")
            for f in findings:
                print(f"\n  Advisor: {f['advisor_id']}")
                print(f"  Title: {f['title']}")
                print(f"  Skills: {', '.join(f.get('closing_skills', []))}")
        else:
            print(f"No findings found for domain '{domain}'")

    elif args[0] == 'status' and len(args) >= 2:
        advisor_id = args[1]
        advisor = load_advisor(advisor_id)
        if advisor:
            print(json.dumps(advisor, indent=2))
        else:
            print(f"Advisor {advisor_id} not found", file=sys.stderr)

    else:
        print(__doc__)
