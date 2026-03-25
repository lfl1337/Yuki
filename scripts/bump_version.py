#!/usr/bin/env python3
"""
Bump version across all Yuki v2 version references.

Usage:
    python scripts/bump_version.py 2.1.0
    python scripts/bump_version.py --tag 2.1.0    # also creates a git tag
"""

import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

FILES_TO_PATCH = [
    # (relative_path, regex_pattern, replacement_template)
    ("VERSION", r"^\d+\.\d+\.\d+$", "{version}"),
    ("frontend/src-tauri/tauri.conf.json", r'"version": "\d+\.\d+\.\d+"', '"version": "{version}"'),
    ("frontend/src-tauri/Cargo.toml", r'^version = "\d+\.\d+\.\d+"', 'version = "{version}"'),
    ("backend/pyproject.toml", r'^version = "\d+\.\d+\.\d+"', 'version = "{version}"'),
    ("frontend/package.json", r'"version": "\d+\.\d+\.\d+"', '"version": "{version}"'),
    ("backend/app/main.py", r'version="\d+\.\d+\.\d+"', 'version="{version}"'),
    ("backend/app/services/auto_updater.py", r'^VERSION = "\d+\.\d+\.\d+"', 'VERSION = "{version}"'),
    ("frontend/src/components/Sidebar.tsx", r'v\d+\.\d+\.\d+', "v{version}"),
]


def bump(new_version: str, create_tag: bool = False) -> None:
    # Validate semver
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"Error: '{new_version}' is not a valid semver string (expected X.Y.Z)")
        sys.exit(1)

    patched = []
    for rel_path, pattern, template in FILES_TO_PATCH:
        path = ROOT / rel_path
        if not path.exists():
            print(f"  SKIP (not found): {rel_path}")
            continue

        original = path.read_text(encoding="utf-8")
        replacement = template.replace("{version}", new_version)
        updated = re.sub(pattern, replacement, original, flags=re.MULTILINE)

        if updated == original:
            print(f"  UNCHANGED: {rel_path}")
        else:
            path.write_text(updated, encoding="utf-8")
            patched.append(rel_path)
            print(f"  PATCHED:   {rel_path}")

    if not patched:
        print("No files changed.")
        return

    print(f"\nBumped to {new_version} in {len(patched)} file(s).")

    if create_tag:
        subprocess.run(["git", "add"] + [str(ROOT / p) for p in patched], cwd=ROOT, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump version to {new_version}"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(["git", "tag", f"v{new_version}"], cwd=ROOT, check=True)
        print(f"Git commit and tag v{new_version} created.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/bump_version.py [--tag] <version>")
        sys.exit(1)

    tag = "--tag" in args
    version_args = [a for a in args if not a.startswith("--")]
    if not version_args:
        print("Error: missing version argument")
        sys.exit(1)

    bump(version_args[0], create_tag=tag)
