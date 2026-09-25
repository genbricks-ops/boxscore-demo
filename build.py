#!/usr/bin/env python3
"""Build script for Boxscore Demo — compiles React frontend and packages backend for Databricks deployment."""

import os
import subprocess
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
STATIC_DIR = os.path.join(BACKEND_DIR, "static")


def run(cmd, cwd=None):
    print(f"  -> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr}")
        sys.exit(1)
    return result.stdout


def build_frontend():
    print("\n1. Installing frontend dependencies...")
    run(["npm", "install"], cwd=FRONTEND_DIR)

    print("2. Building React app...")
    run(["npm", "run", "build"], cwd=FRONTEND_DIR)

    if not os.path.exists(DIST_DIR):
        print("ERROR: frontend/dist not found after build")
        sys.exit(1)
    print("   Frontend built successfully.")


def copy_static():
    print("\n3. Copying static files to backend...")
    if os.path.exists(STATIC_DIR):
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(DIST_DIR, STATIC_DIR)
    print(f"   Copied to {STATIC_DIR}")


def check_backend():
    print("\n4. Checking backend dependencies...")
    req = os.path.join(BACKEND_DIR, "requirements.txt")
    if not os.path.exists(req):
        print("   WARNING: backend/requirements.txt not found")
    else:
        print("   requirements.txt found.")
    print("   Backend ready.")


def main():
    print("=" * 60)
    print("  Boxscore Demo — Build Script")
    print("=" * 60)

    build_frontend()
    copy_static()
    check_backend()

    print("\n" + "=" * 60)
    print("  Build complete!")
    print("  Deploy with: python deploy_to_databricks.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
