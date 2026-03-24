#!/usr/bin/env python3
"""
Full Yuki release pipeline:
  1. Verify working tree is clean
  2. Build Python backend → .exe sidecar
  3. Build Tauri frontend → NSIS installer
  4. Print output path

Usage:
    python scripts/release.py
    python scripts/release.py --skip-backend   # skip step 2 (use existing .exe)
"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRONTEND = ROOT / "frontend"
BACKEND_EXE = FRONTEND / "src-tauri" / "binaries" / "yuki-backend-x86_64-pc-windows-msvc.exe"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def run(cmd, **kwargs):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"Command failed (exit {result.returncode})")
        sys.exit(1)
    return result


def check_git_clean():
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    )
    if result.stdout.strip():
        print("Working tree is not clean. Commit or stash changes first.")
        sys.exit(1)
    print("  Git: working tree clean.")


def main():
    skip_backend = "--skip-backend" in sys.argv

    print(f"\n{'='*60}")
    print(f"  Yuki Release v{VERSION}")
    print(f"{'='*60}\n")

    print("[1/3] Checking git status…")
    check_git_clean()

    if not skip_backend:
        print("\n[2/3] Building backend sidecar…")
        run([sys.executable, str(ROOT / "scripts" / "build_backend.py")], cwd=ROOT)
    else:
        if not BACKEND_EXE.exists():
            print(f"--skip-backend: but no exe found at {BACKEND_EXE}")
            sys.exit(1)
        size_mb = BACKEND_EXE.stat().st_size / 1024 / 1024
        print(f"\n[2/3] Skipping backend build (existing: {size_mb:.1f} MB)")

    print("\n[3/3] Building Tauri installer…")
    run(["npm", "run", "build"], cwd=FRONTEND)

    # Find installer
    nsis_dir = FRONTEND / "src-tauri" / "target" / "release" / "bundle" / "nsis"
    installers = list(nsis_dir.glob("*.exe")) if nsis_dir.exists() else []
    if installers:
        installer = max(installers, key=lambda p: p.stat().st_mtime)
        size_mb = installer.stat().st_size / 1024 / 1024
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {installer}")
        print(f"  Size:    {size_mb:.1f} MB")
        print(f"  Version: {VERSION}")
        print(f"{'='*60}\n")
    else:
        print("\nBuild completed but installer not found in expected location.")
        print(f"  Expected: {nsis_dir}")


if __name__ == "__main__":
    main()
