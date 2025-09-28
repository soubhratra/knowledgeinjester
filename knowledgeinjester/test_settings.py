"""
Test settings for knowledge injester.
"""
from .settings import *
import os

# Use PostgreSQL test database for Supabase compatibility
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('TEST_DB_NAME', 'test_knowledgeinjester'),
        'USER': os.getenv('TEST_DB_USER', os.getenv('DB_USER', 'postgres')),
        'PASSWORD': os.getenv('TEST_DB_PASSWORD', os.getenv('DB_PASSWORD', '')),
        'HOST': os.getenv('TEST_DB_HOST', os.getenv('DB_HOST', 'localhost')),
        'PORT': os.getenv('TEST_DB_PORT', os.getenv('DB_PORT', '5432')),
        'OPTIONS': {'sslmode': 'require'} if os.getenv('TEST_DB_SSL', 'true').lower() == 'true' else {},
    }
}

# Enable migrations for PostgreSQL tests to ensure proper schema
# MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'
TESTING = True

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Test-specific app settings
MARKDOWN_ROOT = '/tmp/test_markdown'
CACHE_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'

# Mock external services for tests
OPENAI_API_KEY = 'test-openai-key'
SUPABASE_URL = 'https://test.supabase.co'
SUPABASE_ANON_KEY = 'test-anon-key'
SUPABASE_SERVICE_ROLE_KEY = 'test-service-key'

# Test data settings
TEST_DATA_DIR = '/tmp/test_data'


