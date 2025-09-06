"""
Hashing utilities for content idempotency and deduplication.
"""
import hashlib
from typing import Union


def sha256_hash(content: Union[str, bytes]) -> str:
    """
    Generate SHA256 hash of content for idempotency.
    
    Args:
        content: String or bytes to hash
        
    Returns:
        Hexadecimal SHA256 hash
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    return hashlib.sha256(content).hexdigest()


def content_id(content: str, source_url: str) -> str:
    """
    Generate a unique content ID based on content and source URL.
    
    Args:
        content: The content text
        source_url: The source URL
        
    Returns:
        Unique content identifier
    """
    combined = f"{source_url}:{content}"
    return sha256_hash(combined)


def url_hash(url: str) -> str:
    """
    Generate a hash for a URL.
    
    Args:
        url: URL to hash
        
    Returns:
        Hexadecimal hash of the URL
    """
    return sha256_hash(url)


def chunk_hash(content: str, chunk_index: int, total_chunks: int) -> str:
    """
    Generate a hash for a content chunk.
    
    Args:
        content: Chunk content
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks
        
    Returns:
        Unique chunk identifier
    """
    combined = f"{content}:{chunk_index}:{total_chunks}"
    return sha256_hash(combined)


