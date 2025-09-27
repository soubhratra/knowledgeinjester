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
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Database migrations completed")
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        raise

def create_superuser():
    """Create superuser from environment variables if it doesn't exist"""
    print("Checking for superuser...")
    
    # Check if required environment variables are present
    required_vars = ['DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_EMAIL', 'DJANGO_SUPERUSER_PASSWORD']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  Missing superuser environment variables: {', '.join(missing_vars)}")
        print("   Skipping superuser creation. Set these variables to create a superuser automatically.")
        return
    
    try:
        execute_from_command_line(['manage.py', 'create_superuser'])
        print("✅ Superuser check completed")
    except Exception as e:
        print(f"❌ Superuser creation failed: {e}")
        print("   You may need to create a superuser manually")

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.settings')
    django.setup()
    
    setup_database()
    create_superuser()
    
    print("Startup completed successfully!")
