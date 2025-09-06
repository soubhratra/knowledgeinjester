"""
Unit tests for core hashing utilities.
"""
import pytest
from apps.core.hashing import sha256_hash, content_id, url_hash, chunk_hash


class TestHashing:
    """Test hashing utilities."""
    
    def test_sha256_hash_string(self):
        """Test SHA256 hash with string input."""
        content = "Hello, World!"
        result = sha256_hash(content)
        
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 produces 64 hex characters
        assert result == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    
    def test_sha256_hash_bytes(self):
        """Test SHA256 hash with bytes input."""
        content = b"Hello, World!"
        result = sha256_hash(content)
        
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_content_id(self):
        """Test content ID generation."""
        content = "Test content"
        url = "https://example.com"
        result = content_id(content, url)
        
        assert isinstance(result, str)
        assert len(result) == 64
        
        # Should be deterministic
        result2 = content_id(content, url)
        assert result == result2
    
    def test_url_hash(self):
        """Test URL hashing."""
        url = "https://example.com/page"
        result = url_hash(url)
        
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_chunk_hash(self):
        """Test chunk hashing."""
        content = "Test chunk content"
        chunk_index = 0
        total_chunks = 5
        result = chunk_hash(content, chunk_index, total_chunks)
        
        assert isinstance(result, str)
        assert len(result) == 64
        
        # Different chunks should have different hashes
        result2 = chunk_hash(content, 1, total_chunks)
        assert result != result2
    
    def test_empty_content(self):
        """Test hashing with empty content."""
        result = sha256_hash("")
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_unicode_content(self):
        """Test hashing with unicode content."""
        content = "Hello, 世界! 🌍"
        result = sha256_hash(content)
        
        assert isinstance(result, str)
        assert len(result) == 64


