#!/usr/bin/env python3
"""
Startup script for production deployment.
This script handles database migrations and superuser creation.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_database():
    """Run database migrations"""
    print("Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate'])

def create_superuser():
    """Create superuser from environment variables if it doesn't exist"""
    print("Checking for superuser...")
    try:
        execute_from_command_line(['manage.py', 'create_superuser'])
    except Exception as e:
        print(f"Superuser creation failed: {e}")
        print("You may need to create a superuser manually")

def collect_static():
    """Collect static files for production"""
    print("Collecting static files...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.settings')
    django.setup()
    
    setup_database()
    create_superuser()
    collect_static()
    
    print("Startup completed successfully!")
