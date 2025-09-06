"""
Crawler services for web content extraction.
"""
import asyncio
from typing import List, Optional

from apps.core.types import PageRaw
from apps.core.logging import get_logger
from .simple_crawl4ai import crawl_site

logger = get_logger(__name__)


async def crawl_website(
    root_url: str, 
    max_pages: int = 100,
    tenant_id: Optional[str] = None
) -> List[PageRaw]:
    """
    Crawl a website and return raw page data.
    
    Args:
        root_url: Root URL to start crawling from
        max_pages: Maximum number of pages to crawl
        tenant_id: Optional tenant identifier
        
    Returns:
        List of raw page data
    """
    logger.info(f"Starting crawl of {root_url} (max_pages={max_pages})")
    
    try:
        # This is a simplified version - in practice you'd want to modify
        # the crawl_site function to return PageRaw objects instead of just saving files
        await crawl_site(root_url, max_pages)
        
        # For now, return empty list - in a real implementation you'd parse
        # the saved markdown files and return PageRaw objects
        logger.info(f"Completed crawl of {root_url}")
        return []
        
    except Exception as e:
        logger.error(f"Failed to crawl {root_url}: {e}")
        raise


def crawl_website_sync(
    root_url: str, 
    max_pages: int = 100,
    tenant_id: Optional[str] = None
) -> List[PageRaw]:
    """
    Synchronous wrapper for crawl_website.
    
    Args:
        root_url: Root URL to start crawling from
        max_pages: Maximum number of pages to crawl
        tenant_id: Optional tenant identifier
        
    Returns:
        List of raw page data
    """
    return asyncio.run(crawl_website(root_url, max_pages, tenant_id))


