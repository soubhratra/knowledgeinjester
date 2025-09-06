"""
Test settings for knowledge injester.
"""
from .settings import *

# Use in-memory database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

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


