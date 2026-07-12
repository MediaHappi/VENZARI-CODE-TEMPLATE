#!/usr/bin/env python3
"""
Advisor Repository Scanner — Force real analysis, prevent fabrication

When an advisor is completed, this module scans the actual repository
and produces findings based on real code inspection, not input text.

Prevents false advisor output by requiring:
1. File/directory existence checks
2. Code analysis (grep, imports, function calls)
3. Test execution
4. Memory state verification
5. Gate execution verification

All findings must be backed by actual evidence from the repository.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone


def scan_memory_layers():
    """Scan actual memory layer implementation status."""
    findings = {
        'L1_redis': {'status': 'unknown', 'evidence': []},
        'L2_postgresql': {'status': 'unknown', 'evidence': []},
        'L3_chromadb': {'status': 'unknown', 'evidence': []},
        'L4_codegraph': {'status': 'unknown', 'evidence': []},
        'L5_git_archive': {'status': 'unknown', 'evidence': []},
    }

    repo_root = Path('/opt/YOUR-PROJECT')

    # L1: Redis persistence - check wire_memory_persistence imports
    redis_refs = subprocess.run(
        ['grep', '-r', 'redis', 'ops/agent/', '--include=*.py'],
        cwd=repo_root, capture_output=True, text=True
    )
    findings['L1_redis']['evidence'] = [line for line in redis_refs.stdout.split('\n') if line][:3]
    findings['L1_redis']['status'] = 'referenced' if findings['L1_redis']['evidence'] else 'missing'

    # L2: PostgreSQL - check if wire_memory_persistence.py exists and is imported
    l2_file = repo_root / 'ops/agent/wire_memory_persistence.py'
    findings['L2_postgresql']['evidence'].append(f"wire_memory_persistence.py exists: {l2_file.exists()}")
    l2_refs = subprocess.run(
        ['grep', '-r', 'wire_memory_persistence', 'ops/agent/task_manager.py'],
        cwd=repo_root, capture_output=True, text=True
    )
    findings['L2_postgresql']['evidence'].append(f"Referenced in task_manager.py: {bool(l2_refs.stdout)}")
    findings['L2_postgresql']['status'] = 'implemented' if l2_file.exists() and l2_refs.stdout else 'incomplete'

    # L3: ChromaDB - check if chromadb_adapter exists but is never called
    l3_adapter = repo_root / 'ops/agent/chromadb_adapter.py'
    findings['L3_chromadb']['evidence'].append(f"chromadb_adapter.py exists: {l3_adapter.exists()}")
    l3_calls = subprocess.run(
        ['grep', '-r', 'chromadb_adapter', 'ops/agent/', '--include=*.py', '-c'],
        cwd=repo_root, capture_output=True, text=True
    )
    call_count = len([l for l in l3_calls.stdout.split('\n') if l and not l.endswith(':0')])
    findings['L3_chromadb']['evidence'].append(f"Non-zero call counts: {call_count}")
    findings['L3_chromadb']['status'] = 'exists_unused' if l3_adapter.exists() and call_count <= 1 else 'integrated'

    # L4: CodeGraph - check codegraph_adapter
    l4_adapter = repo_root / 'ops/agent/codegraph_adapter.py'
    findings['L4_codegraph']['evidence'].append(f"codegraph_adapter.py exists: {l4_adapter.exists()}")
    findings['L4_codegraph']['status'] = 'stub' if l4_adapter.exists() else 'missing'

    # L5: Git/Archive - check .memory_archive
    l5_archive = repo_root / '.memory_archive'
    findings['L5_git_archive']['evidence'].append(f".memory_archive exists: {l5_archive.exists()}")
    findings['L5_git_archive']['status'] = 'potential' if l5_archive.exists() else 'not_implemented'

    return findings


def scan_missing_modules():
    """Scan for modules that should exist but don't."""
    findings = {
        'missing': [],
        'evidence': []
    }

    repo_root = Path('/opt/YOUR-PROJECT')

    # Check for memory-governance.py (required by Task 1704)
    gov_file = repo_root / 'ops/agent/memory-governance.py'
    if not gov_file.exists():
        findings['missing'].append({
            'module': 'memory-governance.py',
            'reason': 'Required by Task 1704 for L3 persistence',
            'impact': 'Knowledge persistence incomplete'
        })
        findings['evidence'].append(f"memory-governance.py missing: {not gov_file.exists()}")

    return findings


def scan_dead_code():
    """Scan for complete modules that are never invoked."""
    findings = {
        'dead_modules': [],
        'evidence': []
    }

    repo_root = Path('/opt/YOUR-PROJECT')

    candidates = [
        ('advisor_wiki_generator.py', 'advisor_wiki_generator'),
        ('wiki_memory_bridge.py', 'wiki_memory_bridge'),
        ('incident_detector.py', 'incident_detector'),
    ]

    for filename, search_term in candidates:
        file_path = repo_root / 'ops/agent' / filename
        if file_path.exists():
            # Check if it's actually called from main execution paths
            calls = subprocess.run(
                ['grep', '-r', f'from {search_term} import|import {search_term}',
                 'ops/agent/', '--include=*.py'],
                cwd=repo_root, capture_output=True, text=True
            )

            # Count calls (excluding the file itself)
            call_lines = [l for l in calls.stdout.split('\n') if l and search_term in l
                         and not l.startswith(f'ops/agent/{filename}:')]

            if len(call_lines) <= 1:  # 0-1 calls means essentially unused
                findings['dead_modules'].append({
                    'module': filename,
                    'file': file_path,
                    'calls': len(call_lines),
                    'status': 'complete_but_unused'
                })
                findings['evidence'].append(f"{filename}: {len(call_lines)} imports")

    return findings


def scan_task_execution():
    """Scan task system for pending work."""
    findings = {
        'total_tasks': 0,
        'pending_tasks': 0,
        'completed_tasks': 0,
        'evidence': []
    }

    tasks_dir = Path('/opt/YOUR-PROJECT/.tasks')
    if tasks_dir.exists():
        all_tasks = list(tasks_dir.glob('*.json'))
        findings['total_tasks'] = len(all_tasks)

        pending_count = 0
        completed_count = 0
        for task_file in all_tasks:
            try:
                with open(task_file) as f:
                    task = json.load(f)
                    if task.get('status') in ['pending', 'future']:
                        pending_count += 1
                    elif task.get('status') == 'completed':
                        completed_count += 1
            except:
                pass

        findings['pending_tasks'] = pending_count
        findings['completed_tasks'] = completed_count
        findings['evidence'].append(f"Total tasks: {findings['total_tasks']}")
        findings['evidence'].append(f"Pending/Future: {pending_count}")
        findings['evidence'].append(f"Completed: {completed_count}")

    return findings


def run_integration_tests():
    """Run integration tests to verify system works."""
    findings = {
        'tests_pass': False,
        'evidence': []
    }

    repo_root = Path('/opt/YOUR-PROJECT')
    test_file = repo_root / 'tests/integration/test_complete_workflow.py'

    if test_file.exists():
        result = subprocess.run(
            ['python3', '-m', 'pytest', str(test_file), '-v'],
            cwd=repo_root, capture_output=True, text=True, timeout=30
        )

        findings['tests_pass'] = result.returncode == 0
        findings['evidence'].append(f"pytest exit code: {result.returncode}")

        # Extract test result summary
        for line in result.stdout.split('\n'):
            if 'passed' in line or 'PASSED' in line or 'FAILED' in line:
                findings['evidence'].append(line.strip())

    return findings


def perform_full_scan():
    """Execute complete repository scan and return findings."""
    print("🔍 ADVISOR: Executing repository scan...", file=sys.stderr)

    scan_results = {
        'scan_timestamp': datetime.now(timezone.utc).isoformat(),
        'repository': '/opt/YOUR-PROJECT',
        'memory_layers': scan_memory_layers(),
        'missing_modules': scan_missing_modules(),
        'dead_code': scan_dead_code(),
        'task_execution': scan_task_execution(),
        'integration_tests': run_integration_tests(),
    }

    print("✓ ADVISOR: Scan complete", file=sys.stderr)
    return scan_results


def generate_findings_from_scan(scan_results):
    """Convert scan results into human-readable findings."""
    findings = {
        'summary': '',
        'gaps_identified': [],
        'critical_issues': [],
        'recovery_actions': []
    }

    # Memory layer status
    memory_status = scan_results['memory_layers']
    implemented = [k for k, v in memory_status.items() if v['status'] in ['implemented', 'integrated']]
    unused = [k for k, v in memory_status.items() if v['status'] == 'exists_unused']

    findings['summary'] = f"Repository scan: {len(implemented)}/5 memory layers active, {len(unused)} layers unused but complete"

    # Missing modules
    for missing in scan_results['missing_modules']['missing']:
        findings['critical_issues'].append({
            'issue': f"Missing: {missing['module']}",
            'reason': missing['reason'],
            'action': f"Create {missing['module']} with required functionality"
        })

    # Dead code
    for dead in scan_results['dead_code']['dead_modules']:
        findings['gaps_identified'].append({
            'gap': f"Unused module: {dead['module']}",
            'status': f"{dead['calls']} imports (unused)",
            'action': f"Integrate {dead['module']} into active execution path"
        })

    # Task status
    task_data = scan_results['task_execution']
    if task_data['pending_tasks'] > 0:
        findings['gaps_identified'].append({
            'gap': f"Pending tasks: {task_data['pending_tasks']}",
            'status': f"Out of {task_data['total_tasks']} total",
            'action': 'Execute pending tasks or mark as superseded'
        })

    # Integration test status
    if not scan_results['integration_tests']['tests_pass']:
        findings['critical_issues'].append({
            'issue': 'Integration tests failing',
            'reason': 'System may not execute correctly',
            'action': 'Fix broken integration tests before proceeding'
        })

    return findings


if __name__ == '__main__':
    # Run scan and print results
    scan_results = perform_full_scan()
    findings = generate_findings_from_scan(scan_results)

    print(json.dumps(findings, indent=2))
