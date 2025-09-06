#!/usr/bin/env python3
"""
Test runner script for knowledge injester.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - FAILED")
        print(f"Return code: {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("🧪 Knowledge Injester Test Suite")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(project_root)
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.test_settings')
    
    # Test commands
    tests = [
        ("python manage.py check", "Django system check"),
        ("python manage.py makemigrations --dry-run", "Django migrations check"),
        ("pytest tests/unit/ -v", "Unit tests"),
        ("pytest tests/integration/ -v", "Integration tests"),
        ("pytest tests/ -v --cov=apps --cov-report=term-missing", "Full test suite with coverage"),
    ]
    
    # Run tests
    all_passed = True
    for cmd, description in tests:
        if not run_command(cmd, description):
            all_passed = False
            break
    
    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

