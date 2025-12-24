#!/usr/bin/env python3
"""
Script to automatically add override_get_db fixture to test methods
that need database mocking.
"""

import re
import sys
from pathlib import Path


def fix_test_file(file_path: Path) -> tuple[int, int]:
    """
    Add override_get_db to test methods that need it.

    Returns:
        tuple: (number of methods fixed, total methods checked)
    """
    print(f"\n📄 Processing: {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Pattern 1: Test methods with auth that DON'T have override_get_db
    # Matches: def test_xxx(self, client, mock_authenticated_user, auth_headers)
    # But NOT if override_get_db is already there
    pattern1 = re.compile(
        r'(def test_\w+\(\s*'
        r'self,\s*'
        r'client:\s*TestClient,\s*'
        r'mock_authenticated_user:\s*str,\s*'
        r'auth_headers:\s*dict)'
        r'(?!,\s*override_get_db)'  # Negative lookahead - don't match if override_get_db exists
        r'(\s*\))',
        re.MULTILINE
    )

    # Replace by adding override_get_db
    content = pattern1.sub(r'\1,\n        override_get_db\2', content)

    # Pattern 2: Test methods that use create_test_xxx fixtures (need db_session)
    pattern2 = re.compile(
        r'(def test_\w+\(\s*'
        r'self,\s*'
        r'[^)]*'
        r'create_test_[a-z]+)'
        r'(?!.*override_get_db)'  # Don't match if override_get_db exists
        r'([^)]*\))',
        re.MULTILINE | re.DOTALL
    )

    changes_made = len(pattern1.findall(original_content))

    if content != original_content:
        # Backup original
        backup_path = file_path.with_suffix('.py.bak')
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"  💾 Backup created: {backup_path}")

        # Write fixed content
        with open(file_path, 'w') as f:
            f.write(content)

        print(f"  ✅ Fixed {changes_made} test method(s)")
        return changes_made, changes_made
    else:
        print(f"  ✓ No changes needed")
        return 0, 0


def main():
    """Main entry point."""
    print("🔧 Auto-fixing test database fixtures...\n")

    test_dir = Path(__file__).parent / 'tests'

    test_files = [
        test_dir / 'test_cvs.py',
        test_dir / 'test_jobs.py',
        test_dir / 'test_profiles.py',
    ]

    total_fixed = 0
    total_checked = 0

    for file_path in test_files:
        if file_path.exists():
            fixed, checked = fix_test_file(file_path)
            total_fixed += fixed
            total_checked += checked
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n{'='*60}")
    print(f"✨ Complete! Fixed {total_fixed} test methods")
    print(f"{'='*60}")

    print("\n📝 Next steps:")
    print("1. Review the changes:")
    print("   git diff tests/")
    print("\n2. Run tests to verify:")
    print("   pytest tests/ -v")
    print("\n3. If satisfied, remove backup files:")
    print("   rm tests/*.bak")

    return 0 if total_fixed >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
