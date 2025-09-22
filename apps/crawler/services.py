"""
Crawler services for web content extraction.
"""
import asyncio
from typing import List, Optional
from enum import Enum

from apps.core.types import PageRaw
from apps.core.logging import get_logger
from .simple_crawl4ai import crawl_site_with_data
from .llm_crawler import crawl_with_llm_deep_crawling

logger = get_logger(__name__)


class CrawlerType(Enum):
    """Available crawler types."""
    COMPREHENSIVE = "comprehensive"  # Original JsonCssExtractionStrategy
    LLM = "llm"  # New LLM-based extraction


async def crawl_website(
    root_url: str, 
    max_pages: int = 100,
    tenant_id: Optional[str] = None,
    crawler_type: CrawlerType = CrawlerType.LLM,
    max_depth: int = 5
) -> List[PageRaw]:
    """
    Crawl a website and return raw page data.
    
    Args:
        root_url: Root URL to start crawling from
        max_pages: Maximum number of pages to crawl
        tenant_id: Optional tenant identifier
        crawler_type: Type of crawler to use (COMPREHENSIVE or LLM)
        max_depth: Maximum depth for deep crawling (only used with LLM crawler)
        
    Returns:
        List of raw page data
    """
    logger.info(f"Starting {crawler_type.value} crawl of {root_url} (max_pages={max_pages})")
    
    try:
        if crawler_type == CrawlerType.LLM:
            # Use LLM-based crawler with deep crawling
            pages = await crawl_with_llm_deep_crawling(
                root_url, max_pages, max_depth, tenant_id
            )
        else:
            # Use comprehensive crawler (original implementation)
            pages = await crawl_site_with_data(root_url, max_pages)
        
        logger.info(f"Completed {crawler_type.value} crawl of {root_url}, found {len(pages)} pages")
        return pages
        
    except Exception as e:
        logger.error(f"Failed to crawl {root_url} with {crawler_type.value} crawler: {e}")
        raise


def crawl_website_sync(
    root_url: str, 
    max_pages: int = 100,
    tenant_id: Optional[str] = None,
    crawler_type: CrawlerType = CrawlerType.LLM,
    max_depth: int = 5
) -> List[PageRaw]:
    """
    Synchronous wrapper for crawl_website.
    
    Args:
        root_url: Root URL to start crawling from
        max_pages: Maximum number of pages to crawl
        tenant_id: Optional tenant identifier
        crawler_type: Type of crawler to use (COMPREHENSIVE or LLM)
        max_depth: Maximum depth for deep crawling (only used with LLM crawler)
        
    Returns:
        List of raw page data
    """
    return asyncio.run(crawl_website(root_url, max_pages, tenant_id, crawler_type, max_depth))


