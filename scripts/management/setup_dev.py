#!/usr/bin/env python3
"""
Development setup script for knowledge injester.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
    else:
        print(f"❌ {description} - FAILED")
        return False
    
    return True


def main():
    """Setup development environment."""
    print("🚀 Knowledge Injester Development Setup")
    print("=" * 60)
    
    # Change to project directory
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.settings')
    
    # Setup commands
    setup_commands = [
        ("python -m pip install --upgrade pip", "Upgrade pip"),
        ("pip install -r requirements.txt", "Install dependencies"),
        ("pip install pytest pytest-django pytest-cov", "Install test dependencies"),
        ("python manage.py makemigrations", "Create migrations"),
        ("python manage.py migrate", "Run migrations"),
        ("python manage.py check", "Django system check"),
    ]
    
    # Run setup commands
    all_passed = True
    for cmd, description in setup_commands:
        if not run_command(cmd, description):
            all_passed = False
            break
    
    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 Development setup completed!")
        print("\nNext steps:")
        print("1. Copy .env.sample to .env and configure your environment variables")
        print("2. Run tests: python scripts/management/run_tests.py")
        print("3. Start development server: python manage.py runserver")
    else:
        print("💥 Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

