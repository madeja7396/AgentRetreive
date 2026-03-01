#!/usr/bin/env python3
"""Initialize a new project from TEMPLATE/.

Usage:
    python3 scripts/dev/init_project_from_template.py --target /path/to/new-project --name ProjectName

Example:
    python3 scripts/dev/init_project_from_template.py \\
        --target /tmp/AgentRetrieve-foo \\
        --name "AgentRetrieve-Foo" \\
        --owner "research-team" \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_template_dir() -> Path:
    """Get TEMPLATE directory path."""
    return Path(__file__).resolve().parents[2] / "TEMPLATE"


def validate_template_dir(template_dir: Path) -> bool:
    """Check if TEMPLATE directory exists and has required files."""
    if not template_dir.exists():
        print(f"Error: TEMPLATE directory not found: {template_dir}", file=sys.stderr)
        return False
    
    required_files = ["README.md", "PROJECT_STRUCTURE.md"]
    for fname in required_files:
        fpath = template_dir / fname
        if not fpath.exists():
            print(f"Error: Required file not found in TEMPLATE: {fname}", file=sys.stderr)
            return False
    
    return True


def copy_template(template_dir: Path, target_dir: Path, dry_run: bool = False) -> list[Path]:
    """Copy template files to target directory."""
    copied: list[Path] = []
    
    # Exclusion patterns
    exclude_patterns = [
        "*.pyc",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "*.tmp",
        "*.bak",
    ]
    
    for src_path in template_dir.rglob("*"):
        # Check exclusion
        if any(src_path.match(p) for p in exclude_patterns):
            continue
        
        # Compute relative path
        rel_path = src_path.relative_to(template_dir)
        dst_path = target_dir / rel_path
        
        if src_path.is_dir():
            if dry_run:
                print(f"[dry-run] mkdir: {dst_path}")
            else:
                dst_path.mkdir(parents=True, exist_ok=True)
            copied.append(dst_path)
        elif src_path.is_file():
            if dry_run:
                print(f"[dry-run] copy: {src_path} -> {dst_path}")
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            copied.append(dst_path)
    
    # Copy additional files from main project if not in TEMPLATE
    additional_files = [
        ("pyproject.toml", "pyproject.toml"),
    ]
    
    main_project = template_dir.parent
    for src_rel, dst_rel in additional_files:
        src = main_project / src_rel
        dst = target_dir / dst_rel
        if src.exists() and not dst.exists():
            if dry_run:
                print(f"[dry-run] copy: {src} -> {dst}")
            else:
                shutil.copy2(src, dst)
            copied.append(dst)
    
    return copied


def substitute_placeholders(target_dir: Path, project_name: str, owner: str) -> None:
    """Replace placeholders in target files."""
    placeholders = {
        "{{PROJECT_NAME}}": project_name,
        "{{OWNER}}": owner,
        "{{INIT_DATE}}": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "{{TEMPLATE_SOURCE}}": "AgentRetrieve/TEMPLATE",
    }
    
    # Target files for substitution
    target_extensions = {".md", ".json", ".yaml", ".yml", ".py", ".sh", ".txt"}
    
    for fpath in target_dir.rglob("*"):
        if not fpath.is_file():
            continue
        if fpath.suffix not in target_extensions:
            continue
        
        content = fpath.read_text(encoding="utf-8")
        original = content
        
        for placeholder, value in placeholders.items():
            content = content.replace(placeholder, value)
        
        if content != original:
            fpath.write_text(content, encoding="utf-8")
            print(f"  [substituted] {fpath}")


def create_project_structure(target_dir: Path, project_name: str) -> None:
    """Create initial project structure."""
    # Create directories
    dirs = [
        "src",
        "tests/unit",
        "contracts/schemas",
        "scripts/ci",
        "scripts/dev",
        "artifacts",
    ]
    
    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
    
    # Create minimal __init__.py
    (target_dir / "src" / "__init__.py").write_text("""\"\"\"{} package.\"\"\"
""".format(project_name.lower().replace("-", "_")))
    
    (target_dir / "tests" / "__init__.py").touch()
    (target_dir / "tests" / "unit" / "__init__.py").touch()
    
    # Create minimal pyproject.toml if not exists
    pyproject_path = target_dir / "pyproject.toml"
    if not pyproject_path.exists():
        pyproject_path.write_text(f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{project_name} project"
readme = "README.md"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
''')
    
    # Create minimal validate_contracts.py if not exists
    validate_script = target_dir / "scripts" / "ci" / "validate_contracts.py"
    if not validate_script.exists():
        validate_script.write_text('''#!/usr/bin/env python3
"""Minimal contract validation."""
from pathlib import Path
import json
import sys

def main():
    root = Path(__file__).resolve().parents[2]
    schema_dir = root / "contracts" / "schemas"
    if not schema_dir.exists():
        schema_dir = root / "docs" / "schemas"
    if not schema_dir.exists():
        print("No schemas to validate")
        return 1
    
    errors = 0
    files = sorted(schema_dir.glob("*.json"))
    if not files:
        print("No schema files found")
        return 1
    for schema_file in files:
        try:
            json.loads(schema_file.read_text(encoding="utf-8"))
            print(f"[OK] {{schema_file.name}}")
        except Exception as e:
            print(f"[FAIL] {{schema_file.name}}: {{e}}")
            errors += 1
    
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
''')
        validate_script.chmod(0o755)


def run_smoke_tests(target_dir: Path) -> tuple[bool, list[str]]:
    """Run smoke tests on generated project."""
    errors: list[str] = []
    
    # Check 1: Required files exist
    required_files = [
        "README.md",
        "pyproject.toml",
        "contracts/schemas",
        "scripts/ci/validate_contracts.py",
        "scripts/dev/sync_template_bundle.py",
        "tests",
    ]
    
    for fname in required_files:
        fpath = target_dir / fname
        if not fpath.exists():
            errors.append(f"Missing required file: {fname}")
    
    # Check 2: Schema files are valid JSON
    schema_dir = target_dir / "contracts" / "schemas"
    if not schema_dir.exists():
        schema_dir = target_dir / "docs" / "schemas"
    if schema_dir.exists():
        json_files = sorted(schema_dir.glob("*.json"))
        if not json_files:
            errors.append(f"No schema files found in {schema_dir}")
        for schema_file in json_files:
            try:
                json.loads(schema_file.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"Invalid JSON in {schema_file}: {e}")
    
    # Check 3: Python syntax in scripts
    scripts_dir = target_dir / "scripts"
    if scripts_dir.exists():
        for py_file in scripts_dir.rglob("*.py"):
            try:
                import py_compile
                py_compile.compile(str(py_file), doraise=True)
            except Exception as e:
                errors.append(f"Syntax error in {py_file}: {e}")

    # Check 4: At least one runnable test file exists.
    test_files = sorted((target_dir / "tests").rglob("test_*.py"))
    if not test_files:
        errors.append("No test_*.py files found under tests/")

    # Check 5: Verify helper scripts are executable in generated project.
    try:
        subprocess.run(
            ["python3", "scripts/ci/validate_contracts.py"],
            cwd=str(target_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        errors.append(f"validate_contracts.py execution failed: {e}")
    try:
        subprocess.run(
            ["python3", "scripts/dev/sync_template_bundle.py", "--check"],
            cwd=str(target_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        errors.append(f"sync_template_bundle.py --check failed: {e}")
    
    return len(errors) == 0, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a new project from TEMPLATE/",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target directory for new project",
    )
    parser.add_argument(
        "--name",
        default="NewProject",
        help="Project name (default: NewProject)",
    )
    parser.add_argument(
        "--owner",
        default="core_quality",
        help="Project owner (default: core_quality)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without executing",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip smoke tests after initialization",
    )
    args = parser.parse_args()
    
    template_dir = get_template_dir()
    target_dir = Path(args.target).resolve()
    
    print("=" * 60)
    print("PROJECT INITIALIZATION FROM TEMPLATE")
    print("=" * 60)
    print(f"Template: {template_dir}")
    print(f"Target:   {target_dir}")
    print(f"Name:     {args.name}")
    print(f"Owner:    {args.owner}")
    print(f"Dry-run:  {args.dry_run}")
    print("=" * 60)
    
    # Validate
    if not validate_template_dir(template_dir):
        return 1
    
    if target_dir.exists() and any(target_dir.iterdir()):
        print(f"Error: Target directory exists and is not empty: {target_dir}", file=sys.stderr)
        return 1
    
    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")
    
    # Create target directory
    if args.dry_run:
        print(f"[dry-run] mkdir: {target_dir}")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy template
    print("\n[1/4] Copying template files...")
    copied = copy_template(template_dir, target_dir, dry_run=args.dry_run)
    print(f"  Copied: {len(copied)} files/directories")
    
    # Create project structure
    if not args.dry_run:
        print("\n[2/4] Creating project structure...")
        create_project_structure(target_dir, args.name)
        print(f"  Created: src/, tests/, docs/, scripts/, artifacts/")
    else:
        print("\n[2/4] Creating project structure... (dry-run)")
    
    # Substitute placeholders
    if not args.dry_run:
        print("\n[3/4] Substituting placeholders...")
        substitute_placeholders(target_dir, args.name, args.owner)
    else:
        print("\n[3/4] Substituting placeholders... (dry-run)")
    
    # Smoke tests
    if not args.skip_smoke and not args.dry_run:
        print("\n[4/4] Running smoke tests...")
        passed, errors = run_smoke_tests(target_dir)
        if passed:
            print("  [PASS] All smoke tests passed")
        else:
            print("  [FAIL] Smoke tests failed:")
            for err in errors:
                print(f"    - {err}")
            return 1
    else:
        print("\n[4/4] Running smoke tests... (skipped)")
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
    else:
        print("INITIALIZATION COMPLETE")
        print(f"\nNext steps:")
        print(f"  cd {target_dir}")
        print(f"  python3 scripts/ci/validate_contracts.py")
        print(f"  pytest -q")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
