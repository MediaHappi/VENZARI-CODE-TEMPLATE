#!/usr/bin/env python3
"""
SESSION ENFORCEMENT LAYER — Make the rules unbreakable

When any Claude Code session starts, this validates that:
1. Task system is operational
2. Enforcement mechanisms are in place
3. Required files exist
4. Git hooks are live
5. Memory systems are accessible

If ANY check fails → session CANNOT proceed
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_DIR = Path("/opt/YOUR-PROJECT")
REQUIRED_DIRS = [
    ".tasks",
    ".worktrees",
    "ops/agent",
    "system-map",
    ".git/hooks"
]

REQUIRED_FILES = [
    "system-map/CURRENT_STATE.md",
    "GOLDEN_RULES.md",
    "ops/agent/task_manager.py",
    "ops/agent/skill_loader.py",
    "ops/agent/inject_context.py",
    ".git/hooks/pre-commit"
]

REQUIRED_ENFORCEMENT_MODULES = [
    "ops/agent/drift_scanner.py",
    "ops/agent/role_enforcer.py",
    "ops/agent/state_machine_enforcer.py",
    "ops/agent/contradiction_detector.py",
    "ops/agent/evidence_validator.py"
]


def check_repo_root():
    """Verify we're in YOUR-PROJECT repo"""
    if not REPO_DIR.exists():
        print(f"❌ FATAL: YOUR-PROJECT not found at {REPO_DIR}")
        return False

    git_dir = REPO_DIR / ".git"
    if not git_dir.exists():
        print(f"❌ FATAL: Not a git repository: {REPO_DIR}")
        return False

    print(f"✅ Repo root: {REPO_DIR}")
    return True


def check_required_structure():
    """Verify all required directories and files exist"""
    print("\n🔍 Checking repository structure...")

    all_exist = True

    for dirname in REQUIRED_DIRS:
        path = REPO_DIR / dirname
        if path.exists():
            print(f"  ✅ {dirname}")
        else:
            print(f"  ❌ {dirname} MISSING")
            all_exist = False

    for filename in REQUIRED_FILES:
        path = REPO_DIR / filename
        if path.exists():
            print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} MISSING")
            all_exist = False

    return all_exist


def check_enforcement_modules():
    """Verify all enforcement modules exist and are importable"""
    print("\n🔍 Checking enforcement modules...")

    all_importable = True

    for module in REQUIRED_ENFORCEMENT_MODULES:
        path = REPO_DIR / module
        if not path.exists():
            print(f"  ❌ {module} MISSING")
            all_importable = False
            continue

        # Try to import
        try:
            spec_path = str(path)
            result = subprocess.run(
                ["python3", "-m", "py_compile", spec_path],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✅ {module}")
            else:
                print(f"  ❌ {module} (syntax error)")
                all_importable = False
        except Exception as e:
            print(f"  ❌ {module} (error: {e})")
            all_importable = False

    return all_importable


def check_git_hooks():
    """Verify git hooks are installed and executable"""
    print("\n🔍 Checking git hooks...")

    hook_file = REPO_DIR / ".git/hooks/pre-commit"

    if not hook_file.exists():
        print(f"  ❌ pre-commit hook missing")
        return False

    if not hook_file.stat().st_mode & 0o111:
        print(f"  ❌ pre-commit hook not executable")
        return False

    # Verify hook content contains enforcement
    content = hook_file.read_text()
    if "claude-code-gate.py" not in content:
        print(f"  ❌ pre-commit hook doesn't call claude-code-gate")
        return False

    print(f"  ✅ pre-commit hook installed and executable")
    return True


def check_task_system():
    """Verify task system is operational"""
    print("\n🔍 Checking task system...")

    try:
        result = subprocess.run(
            ["python3", "ops/agent/task_manager.py", "list"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"  ✅ Task manager operational")

            # Count pending tasks
            if "pending" in result.stdout:
                print(f"  ✅ Pending tasks exist")
                return True
            else:
                print(f"  ⚠️  No pending tasks (ok for now)")
                return True
        else:
            print(f"  ❌ Task manager failed: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ Task manager timeout")
        return False
    except Exception as e:
        print(f"  ❌ Task manager error: {e}")
        return False


def check_memory_systems():
    """Verify memory layer connections (ChromaDB, PostgreSQL)"""
    print("\n🔍 Checking memory systems...")

    # Check ChromaDB
    try:
        result = subprocess.run(
            ["curl", "-s", "-w", "%{http_code}", "http://127.0.0.1:8001/api/v2/heartbeat"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "200" in result.stdout or "heartbeat" in result.stdout:
            print(f"  ✅ ChromaDB (127.0.0.1:8001) reachable")
        else:
            print(f"  ⚠️  ChromaDB not responding (may be ok if not needed)")
    except Exception as e:
        print(f"  ⚠️  ChromaDB check failed: {e}")

    # Check PostgreSQL (optional - may not be running in all envs)
    try:
        result = subprocess.run(
            ["bash", "-c", "pg_isready -h 127.0.0.1 -p 5432"],
            capture_output=True,
            timeout=5
        )

        if result.returncode == 0 or "accepting" in result.stdout:
            print(f"  ✅ PostgreSQL (127.0.0.1:5432) reachable")
        else:
            print(f"  ⚠️  PostgreSQL not responding (optional)")
    except Exception as e:
        print(f"  ⚠️  PostgreSQL check failed (optional): {e}")

    return True


def check_current_state():
    """Verify CURRENT_STATE.md is readable and valid"""
    print("\n🔍 Checking CURRENT_STATE.md...")

    state_file = REPO_DIR / "system-map/CURRENT_STATE.md"

    if not state_file.exists():
        print(f"  ❌ CURRENT_STATE.md missing")
        return False

    try:
        content = state_file.read_text()
        if len(content) < 100:
            print(f"  ❌ CURRENT_STATE.md too small (not initialized)")
            return False

        if "Service" in content or "service" in content.lower():
            print(f"  ✅ CURRENT_STATE.md readable and populated")
            return True
        else:
            print(f"  ⚠️  CURRENT_STATE.md may be incomplete")
            return True
    except Exception as e:
        print(f"  ❌ Error reading CURRENT_STATE.md: {e}")
        return False


def validate_session():
    """Run ALL checks - if any fail, session cannot proceed"""
    print("\n" + "=" * 80)
    print("YOUR-PROJECT SESSION ENFORCEMENT VALIDATION")
    print("=" * 80)

    checks = [
        ("Repo root", check_repo_root),
        ("Required structure", check_required_structure),
        ("Enforcement modules", check_enforcement_modules),
        ("Git hooks", check_git_hooks),
        ("Task system", check_task_system),
        ("Memory systems", check_memory_systems),
        ("CURRENT_STATE", check_current_state),
    ]

    all_passed = True
    results = {}

    for name, check_fn in checks:
        try:
            passed = check_fn()
            results[name] = passed
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"\n❌ {name} check crashed: {e}")
            results[name] = False
            all_passed = False

    print("\n" + "=" * 80)

    if all_passed:
        print("✅ SESSION VALIDATION PASSED")
        print("=" * 80)
        print("\n🎯 Session ready. Task system is operational.")
        print("   Use: python3 ops/agent/task_manager.py claim <role>")
        return 0
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"❌ SESSION VALIDATION FAILED")
        print(f"   Failed checks: {', '.join(failed)}")
        print("=" * 80)
        print("\n⚠️  CANNOT PROCEED: Fix failures above before starting tasks")
        return 1


if __name__ == "__main__":
    exit_code = validate_session()
    sys.exit(exit_code)
