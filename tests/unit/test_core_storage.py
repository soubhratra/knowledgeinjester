"""
Unit tests for core storage utilities.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings

from apps.core.storage import (
    get_markdown_root, 
    get_domain_folder, 
    get_markdown_path,
    ensure_markdown_root,
    cleanup_old_files
)


class TestStorage:
    """Test storage utilities."""
    
    def test_get_markdown_root_default(self):
        """Test getting default markdown root."""
        with patch.object(settings, 'BASE_DIR', Path('/tmp')):
            root = get_markdown_root()
            assert root == Path('/tmp/test_markdown')  # Updated to match test settings
    
    def test_get_markdown_root_custom(self):
        """Test getting custom markdown root from settings."""
        with patch.object(settings, 'MARKDOWN_ROOT', '/custom/path'):
            root = get_markdown_root()
            assert root == Path('/custom/path')
    
    def test_get_domain_folder(self, temp_markdown_dir):
        """Test domain folder creation."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            folder = get_domain_folder("https://example.com")
            expected = temp_markdown_dir / "example.com"
            assert folder == expected
            assert folder.exists()
    
    def test_get_domain_folder_with_port(self, temp_markdown_dir):
        """Test domain folder with port in URL."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            folder = get_domain_folder("https://example.com:8080")
            expected = temp_markdown_dir / "example.com_8080"
            assert folder == expected
    
    def test_get_markdown_path(self, temp_markdown_dir):
        """Test markdown path generation."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            path = get_markdown_path("https://example.com/page", "Test Page")
            expected = temp_markdown_dir / "example.com" / "page.md"  # URL path takes precedence
            assert path == expected
    
    def test_get_markdown_path_no_title(self, temp_markdown_dir):
        """Test markdown path generation without title."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            path = get_markdown_path("https://example.com/page.html")
            expected = temp_markdown_dir / "example.com" / "page.md"
            assert path == expected
    
    def test_get_markdown_path_index_page(self, temp_markdown_dir):
        """Test markdown path for index page."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            path = get_markdown_path("https://example.com/")
            expected = temp_markdown_dir / "example.com" / "page.md"
            assert path == expected
    
    def test_ensure_markdown_root(self, temp_markdown_dir):
        """Test ensuring markdown root exists."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            ensure_markdown_root()
            assert temp_markdown_dir.exists()
    
    def test_cleanup_old_files(self, temp_markdown_dir):
        """Test cleanup of old files."""
        with patch('apps.core.storage.get_markdown_root', return_value=temp_markdown_dir):
            # Create some test files
            (temp_markdown_dir / "test1.md").write_text("test")
            (temp_markdown_dir / "test2.md").write_text("test")
            
            # Cleanup with 0 days (should delete all)
            deleted = cleanup_old_files(days=0)
            assert deleted == 2
            assert not (temp_markdown_dir / "test1.md").exists()
            assert not (temp_markdown_dir / "test2.md").exists()

