#!/bin/bash
# Test runner script that ensures proper Django setup

# Set Django settings module
export DJANGO_SETTINGS_MODULE=knowledgeinjester.test_settings

# Run pytest with proper configuration
pytest tests/ -v "$@"

