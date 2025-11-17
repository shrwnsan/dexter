#!/usr/bin/env python3
"""
Simple dependency security checker for Dexter
Works around safety permission issues by using pip-audit or basic checks
"""

import subprocess
import sys
import json
from pathlib import Path

def check_dependencies():
    """Check dependencies for known vulnerabilities using pip-audit"""
    print("🔍 Checking dependency security...")

    # Try pip-audit first (comes with newer pip)
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "audit", "--requirement", "requirements.txt"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ No vulnerabilities found with pip-audit")
            return True
        else:
            print("⚠️  pip-audit found vulnerabilities:")
            print(result.stdout)
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ pip-audit failed: {e}")
        return False
    except FileNotFoundError:
        print("⚠️  pip-audit not available, using basic checks...")
        return basic_dependency_check()

def basic_dependency_check():
    """Basic dependency validation without external tools"""
    print("🔍 Running basic dependency validation...")

    try:
        # Check if all requirements can be resolved
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "--dry-run", "--quiet", "-r", "requirements.txt"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ All requirements can be resolved")
            return True
        else:
            print("❌ Some requirements cannot be resolved:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Basic check failed: {e}")
        return False

if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)