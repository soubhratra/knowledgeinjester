# knowledgeinjester/crawler/llm_crawler.py
"""
Fresh and clean implementation of LLM-based deep crawler using Crawl4AI.

This implementation uses Crawl4AI's deep crawling capabilities with LLM extraction
strategies to comprehensively crawl websites and extract structured information.
"""

from __future__ import annotations

import asyncio
import os
import hashlib
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig,
    LLMExtractionStrategy,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
# Removed filter imports - using simple strategy without complex filtering
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

from apps.core.types import PageRaw
from apps.core.logging import get_logger

logger = get_logger(__name__)

# Where to store local markdown files
MARKDOWN_ROOT = Path(__file__).parent / "markdown"

# Skip obvious non-HTML assets
EXCLUDE_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".gz",
    ".mp4", ".webm", ".css", ".js", ".ico", ".woff", ".woff2",
}


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "page"


def _domain_slug(url: str) -> str:
    """Extract domain slug from URL."""
    domain = urlparse(url).netloc or "local"
    return _slugify(domain)


def _folder_for(url: str) -> Path:
    """Create folder for storing markdown files."""
    folder = MARKDOWN_ROOT / _domain_slug(url)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _path_name_from_url(url: str) -> str:
    """Extract meaningful name from URL path."""
    p = urlparse(url)
    segments = [s for s in p.path.split("/") if s]
    if not segments:
        return ""

    leaf = segments[-1]
    leaf_stem = Path(leaf).stem

    # Consider default pages as "not meaningful"
    if leaf_stem.lower() in {"index", "home", "default"}:
        return ""

    return leaf_stem


def _filename_for(url: str, title: str | None, folder: Path) -> str:
    """Generate filename for markdown file."""
    base = _path_name_from_url(url) or (title or "").strip() or "index"
    slug = _slugify(base)

    fname = f"{slug}.md"
    path = folder / fname
    if path.exists():
        # Keep it short but unique by adding a tiny hash from the URL
        short_hash = hashlib.blake2s(url.encode("utf-8"), digest_size=3).hexdigest()
        fname = f"{slug}-{short_hash}.md"
    return fname


def _save_markdown(url: str, title: str | None, markdown: str) -> str:
    """Save markdown content to file with front matter."""
    folder = _folder_for(url)
    fname = _filename_for(url, title, folder)
    path = folder / fname

    # Process the title string to escape quotes outside the f-string
    escaped_title = (title or '').replace('"', '\\"')

    # Minimal front-matter for later indexing
    fm = (
        f"---\n"
        f"title: \"{escaped_title}\"\n"
        f"url: \"{url}\"\n"
        f"crawled_at: \"{datetime.utcnow().isoformat()}Z\"\n"
        f"---\n\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm)
        f.write(markdown or "")
    return str(path)


def _should_skip(url: str) -> bool:
    """Check if URL should be skipped based on extension."""
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in EXCLUDE_EXTS)


def _create_llm_extraction_strategy() -> LLMExtractionStrategy:
    """Create LLM extraction strategy for comprehensive content extraction."""
    
    # Get OpenAI API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for LLM extraction")
    
    # Create LLM config
    llm_config = LLMConfig(
        provider="openai/gpt-4o-mini",
        api_token=api_key
    )
    
    # Create comprehensive instruction for content extraction
    instruction = """
    Extract comprehensive information from this webpage content. Focus on:
    
    1. MAIN CONTENT: Headlines, paragraphs, articles, sections
    2. PRODUCTS & SERVICES: Product names, descriptions, features, benefits
    3. PRICING: All pricing information, costs, fees, rates, discounts, offers
    4. CONTACT INFO: Addresses, phone numbers, emails, social media links
    5. BUSINESS INFO: Company details, about us, team, mission
    6. FAQ & HELP: Questions, answers, help content, documentation
    7. REVIEWS & TESTIMONIALS: Customer reviews, ratings, testimonials
    8. STRUCTURED DATA: Tables, lists, specifications, technical details
    9. NAVIGATION: Menu items, breadcrumbs, internal links
    10. MEDIA: Image descriptions, video content, audio content
    
    For each category, extract as much relevant information as possible.
    Pay special attention to pricing information which might be in various formats:
    - Dollar amounts ($123.45, $1,234.56)
    - Text descriptions ("Starting at $99/month")
    - Muted or hidden pricing in divs
    - Currency symbols and amounts
    - Discount codes and promotional pricing
    
    Return the information in a structured format with clear categories.
    """
    
    return LLMExtractionStrategy(
        llm_config=llm_config,
        extraction_type="block",  # Use block extraction for flexible content
        instruction=instruction,
        chunk_token_threshold=4000,  # Reasonable chunk size for GPT-4o-mini
        overlap_rate=0.1,  # 10% overlap between chunks
        apply_chunking=True,  # Enable chunking for large pages
        input_format="html",  # Use HTML for better structure preservation
        extra_args={
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 2000,  # Reasonable token limit
        },
        verbose=True
    )


def _create_deep_crawl_strategy(
    max_depth: int = 2,
    max_pages: int = 50,
    include_external: bool = False,
    strategy_type: str = "bfs"
) -> BFSDeepCrawlStrategy | BestFirstCrawlingStrategy:
    """Create deep crawling strategy based on type."""
    
    if strategy_type == "best_first":
        # Create keyword scorer for intelligent prioritization
        scorer = KeywordRelevanceScorer(
            keywords=["about", "services", "products", "pricing", "contact", "help", "faq", "documentation"],
            weight=0.7
        )
        
        return BestFirstCrawlingStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages,
            url_scorer=scorer
        )
    else:
        # Default to BFS strategy
        return BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages
        )


async def crawl_with_llm_deep_crawling(
    root_url: str,
    max_pages: int = 50,
    max_depth: int = 2,
    tenant_id: Optional[str] = None,
    strategy_type: str = "bfs"
) -> List[PageRaw]:
    """
    Crawl website using LLM extraction strategy with deep crawling.
    
    Args:
        root_url: Root URL to start crawling from
        max_pages: Maximum number of pages to crawl
        max_depth: Maximum depth for deep crawling
        tenant_id: Optional tenant identifier
        strategy_type: Crawling strategy ("bfs" or "best_first")
        
    Returns:
        List of PageRaw objects with extracted content
    """
    logger.info(f"Starting LLM-based deep crawl of {root_url} (max_pages={max_pages}, max_depth={max_depth}, strategy={strategy_type})")
    
    try:
        # Create LLM extraction strategy
        llm_strategy = _create_llm_extraction_strategy()
        
        # Create deep crawling strategy
        deep_crawl_strategy = _create_deep_crawl_strategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,  # Only crawl internal links
            strategy_type=strategy_type
        )
        
        # Configure markdown generator
        md_gen = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.1, threshold_type="fixed")
        )
        
        # Configure crawler for comprehensive extraction with minimal wait conditions
        run_config = CrawlerRunConfig(
            deep_crawl_strategy=deep_crawl_strategy,
            extraction_strategy=llm_strategy,
            markdown_generator=md_gen,
            cache_mode=CacheMode.BYPASS,
            only_text=False,  # Keep HTML structure for better extraction
            exclude_all_images=False,  # Keep images for alt text
            word_count_threshold=10,
            # Remove wait conditions entirely to avoid timeouts
            page_timeout=30000,  # 30 seconds total page timeout
            delay_before_return_html=1,  # 1 second delay
            remove_overlay_elements=True,
            simulate_user=True,
            js_code="window.scrollTo(0, document.body.scrollHeight);",  # Scroll to load lazy content
            ignore_body_visibility=True,
            verbose=True
        )
        
        pages = []
        
        async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
            # Collect all results at once
            logger.info("Starting deep crawl...")
            results = await crawler.arun(root_url, config=run_config)
            
            # If no results succeeded, try with more lenient configuration
            if not any(result.success for result in results):
                logger.warning("Initial crawl failed, trying with more lenient configuration...")
                fallback_config = CrawlerRunConfig(
                    deep_crawl_strategy=deep_crawl_strategy,
                    extraction_strategy=llm_strategy,
                    markdown_generator=md_gen,
                    cache_mode=CacheMode.BYPASS,
                    only_text=True,  # Simplified text-only mode
                    word_count_threshold=1,
                    # No wait conditions to avoid timeouts
                    page_timeout=20000,  # 20 seconds
                    delay_before_return_html=0.5,  # Minimal delay
                    ignore_body_visibility=True,  # Don't wait for body visibility
                    verbose=True
                )
                results = await crawler.arun(root_url, config=fallback_config)
            
            # If still no results, try ultra-minimal configuration
            if not any(result.success for result in results):
                logger.warning("Fallback crawl failed, trying ultra-minimal configuration...")
                ultra_minimal_config = CrawlerRunConfig(
                    deep_crawl_strategy=deep_crawl_strategy,
                    cache_mode=CacheMode.BYPASS,
                    only_text=True,
                    word_count_threshold=1,
                    page_timeout=15000,  # 15 seconds
                    delay_before_return_html=0.1,  # Very minimal delay
                    ignore_body_visibility=True,
                    # No wait conditions
                    verbose=True
                )
                results = await crawler.arun(root_url, config=ultra_minimal_config)
            
            for result in results:
                if result.success:
                    page = _process_crawl_result(result, tenant_id)
                    if page:
                        pages.append(page)
                        logger.info(f"✓ Crawled: {page.title} (Depth: {result.metadata.get('depth', 0)})")
                else:
                    logger.warning(f"✗ Failed to crawl {result.url}: {result.error_message}")
        
        # If no pages were successfully crawled, create a basic page with URL info
        if not pages:
            logger.warning("No pages were successfully crawled, creating basic page with URL info")
            page = PageRaw(
                url=root_url,
                title=urlparse(root_url).path or root_url,
                content=f"Failed to crawl {root_url}. This page could not be processed due to technical issues or timeouts.",
                metadata={
                    "crawled_at": datetime.now().isoformat(),
                    "word_count": 0,
                    "source": "llm_crawler_failed",
                    "extraction_method": "none",
                    "llm_extracted_content": "",
                    "tenant_id": tenant_id,
                }
            )
            pages.append(page)
            
            # Try to save a basic markdown file
            try:
                saved_to = _save_markdown(root_url, page.title, page.content)
                logger.info(f"Saved basic markdown to: {saved_to}")
            except Exception as e:
                logger.error(f"Failed to save basic markdown: {e}")
        
        # Show LLM usage statistics
        try:
            llm_strategy.show_usage()
        except Exception as e:
            logger.warning(f"Could not show LLM usage: {e}")
        
        logger.info(f"Completed LLM-based deep crawl, found {len(pages)} pages")
        return pages
        
    except Exception as e:
        logger.error(f"Failed to crawl {root_url} with LLM deep crawling: {e}")
        raise


def _process_crawl_result(result, tenant_id: Optional[str] = None) -> Optional[PageRaw]:
    """Process a single crawl result into a PageRaw object."""
    try:
        # Extract title and content
        title = (result.metadata or {}).get("title") if isinstance(result.metadata, dict) else None
        content = getattr(result, "markdown", "") or ""
        
        # Get LLM extracted content
        extracted_content = getattr(result, "extracted_content", "") or ""
        
        # Combine markdown content with LLM extracted content
        enhanced_content = content
        if extracted_content:
            enhanced_content += f"\n\n## AI-Extracted Information\n\n{extracted_content}"
        
        # Create PageRaw object
        page = PageRaw(
            url=result.url,
            title=title or urlparse(result.url).path or result.url,
            content=enhanced_content,
            metadata={
                "crawled_at": datetime.now().isoformat(),
                "word_count": len(enhanced_content.split()) if enhanced_content else 0,
                "source": "llm_crawler",
                "extraction_method": "llm_block_extraction",
                "llm_extracted_content": extracted_content,
                "tenant_id": tenant_id,
                "depth": result.metadata.get("depth", 0) if isinstance(result.metadata, dict) else 0,
                "score": result.metadata.get("score", 0) if isinstance(result.metadata, dict) else 0,
            }
        )
        
        # Save markdown file
        try:
            saved_to = _save_markdown(result.url, title, enhanced_content)
            logger.debug(f"Saved markdown to: {saved_to}")
        except Exception as e:
            logger.error(f"Failed to save markdown for {result.url}: {e}")
        
        return page
        
    except Exception as e:
        logger.error(f"Error processing crawl result for {result.url}: {e}")
        return None


async def crawl_with_llm_extraction_sync(
    root_url: str,
    max_pages: int = 50,
    max_depth: int = 2,
    tenant_id: Optional[str] = None,
    strategy_type: str = "bfs"
) -> List[PageRaw]:
    """
    Synchronous wrapper for LLM-based deep crawling.
    """
    return await crawl_with_llm_deep_crawling(
        root_url, max_pages, max_depth, tenant_id, strategy_type
    )


# Test function
async def test_llm_crawler(url: str, max_pages: int = 5, max_depth: int = 2, strategy: str = "bfs") -> None:
    """
    Test function for LLM crawler.
    """
    print(f"Testing LLM crawler on: {url}")
    print(f"Max pages: {max_pages}, Max depth: {max_depth}, Strategy: {strategy}")
    
    try:
        pages = await crawl_with_llm_deep_crawling(
            url, max_pages, max_depth, strategy_type=strategy
        )
        
        print(f"\n=== LLM CRAWLER RESULTS ===")
        print(f"Total pages crawled: {len(pages)}")
        
        for i, page in enumerate(pages, 1):
            print(f"\n--- Page {i} ---")
            print(f"Title: {page.title}")
            print(f"URL: {page.url}")
            print(f"Depth: {page.metadata.get('depth', 0)}")
            print(f"Score: {page.metadata.get('score', 0):.2f}")
            print(f"Word Count: {page.metadata.get('word_count', 0)}")
            
            # Show LLM extracted content preview
            llm_content = page.metadata.get('llm_extracted_content', '')
            if llm_content:
                print(f"LLM Extracted Content Preview:")
                print(llm_content[:500] + "..." if len(llm_content) > 500 else llm_content)
            else:
                print("No LLM extracted content")
            
            # Show regular content preview
            print(f"Regular Content Preview:")
            print(page.content[:300] + "..." if len(page.content) > 300 else page.content)
        
    except Exception as e:
        print(f"Error during LLM crawling: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        strategy = sys.argv[4] if len(sys.argv) > 4 else "bfs"
        
        asyncio.run(test_llm_crawler(url, max_pages, max_depth, strategy))
    else:
        print("Usage: python -m apps.crawler.llm_crawler <url> [max_pages] [max_depth] [strategy]")
        print("Example: python -m apps.crawler.llm_crawler https://example.com 10 3 best_first")
        print("Strategies: 'bfs' (breadth-first) or 'best_first' (intelligent prioritization)")