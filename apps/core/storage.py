"""
Local filesystem utilities for markdown storage and organization.
"""
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings


def get_markdown_root() -> Path:
    """
    Get the root directory for storing markdown files.
    
    Returns:
        Path to markdown storage directory
    """
    root = getattr(settings, 'MARKDOWN_ROOT', None)
    if root:
        return Path(root)
    
    # Default to project root / markdown
    return Path(settings.BASE_DIR) / 'markdown'


def get_domain_folder(url: str) -> Path:
    """
    Get the folder path for a domain.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Path to domain-specific folder
    """
    domain = urlparse(url).netloc or 'unknown'
    # Sanitize domain name for filesystem
    domain = domain.replace(':', '_').replace('/', '_')
    
    folder = get_markdown_root() / domain
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_markdown_path(url: str, title: Optional[str] = None) -> Path:
    """
    Get the full path for a markdown file.
    
    Args:
        url: Source URL
        title: Optional page title
        
    Returns:
        Path to markdown file
    """
    domain_folder = get_domain_folder(url)
    
    # Generate filename from URL path
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if path_parts:
        filename = path_parts[-1]
        # Remove extension if present
        filename = os.path.splitext(filename)[0]
    else:
        filename = 'index'
    
    # Use title if available and no good filename
    if not filename or filename in ('index', 'home'):
        filename = title or 'page'
    
    # Sanitize filename
    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
    if not filename:
        filename = 'page'
    
    return domain_folder / f"{filename}.md"


def ensure_markdown_root() -> None:
    """Ensure the markdown root directory exists."""
    get_markdown_root().mkdir(parents=True, exist_ok=True)


def cleanup_old_files(days: int = 30) -> int:
    """
    Clean up markdown files older than specified days.
    
    Args:
        days: Number of days to keep files
        
    Returns:
        Number of files deleted
    """
    import time
    from pathlib import Path
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    markdown_root = get_markdown_root()
    if not markdown_root.exists():
        return 0
    
    for file_path in markdown_root.rglob('*.md'):
        if file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()
            deleted_count += 1
    
    return deleted_count


