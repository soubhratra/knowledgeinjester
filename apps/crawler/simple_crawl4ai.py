# knowledgeinjester/crawler/simple_crawl4ai.py
from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque, List, Set
from urllib.parse import urljoin, urlparse
from pathlib import Path, PurePosixPath
from datetime import datetime
import hashlib
import re
from urllib.parse import urlparse

from crawl4ai import (
    AsyncWebCrawler,
    AsyncUrlSeeder,
    SeedingConfig,
    CrawlerRunConfig,
    CacheMode,
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# NEW: where to store local markdown files
MARKDOWN_ROOT = Path(__file__).parent / "markdown"

# Skip obvious non-HTML assets
EXCLUDE_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".gz",
    ".mp4", ".webm", ".css", ".js", ".ico", ".woff", ".woff2",
}

# Comprehensive extraction schema for exhaustive information capture
COMPREHENSIVE_EXTRACTION_SCHEMA = {
    "name": "Comprehensive Website Information",
    "baseSelector": "body",
    "fields": [
        # Core content structure
        {"name": "main_title", "selector": "h1, .main-title, .page-title, [class*='title']", "type": "text"},
        {"name": "subtitle", "selector": "h2, .subtitle, .sub-title, [class*='subtitle']", "type": "text"},
        {"name": "headings", "selector": "h1, h2, h3, h4, h5, h6", "type": "text"},
        {"name": "paragraphs", "selector": "p, .paragraph, [class*='text'], [class*='content']", "type": "text"},
        {"name": "lists", "selector": "ul, ol, .list, [class*='list']", "type": "text"},
        
        # Navigation and structure
        {"name": "navigation", "selector": "nav, .nav, .navigation, .menu, [class*='nav'], [class*='menu']", "type": "text"},
        {"name": "breadcrumbs", "selector": ".breadcrumb, .breadcrumbs, [class*='breadcrumb']", "type": "text"},
        {"name": "sidebar", "selector": ".sidebar, .side-bar, [class*='sidebar']", "type": "text"},
        {"name": "footer", "selector": "footer, .footer, [class*='footer']", "type": "text"},
        
        # Content sections
        {"name": "main_content", "selector": "main, .main, .content, .main-content, [class*='main'], [class*='content']", "type": "text"},
        {"name": "articles", "selector": "article, .article, [class*='article']", "type": "text"},
        {"name": "sections", "selector": "section, .section, [class*='section']", "type": "text"},
        {"name": "cards", "selector": ".card, .card-body, [class*='card']", "type": "text"},
        {"name": "blocks", "selector": ".block, .content-block, [class*='block']", "type": "text"},
        
        # Interactive elements
        {"name": "buttons", "selector": "button, .btn, .button, [class*='btn'], [class*='button']", "type": "text"},
        {"name": "links", "selector": "a, .link, [class*='link']", "type": "text"},
        {"name": "forms", "selector": "form, .form, [class*='form']", "type": "text"},
        {"name": "inputs", "selector": "input, textarea, select, [class*='input']", "type": "text"},
        
        # Data tables and structured content
        {"name": "tables", "selector": "table, .table, [class*='table']", "type": "text"},
        {"name": "table_headers", "selector": "th, .table-header, [class*='header']", "type": "text"},
        {"name": "table_rows", "selector": "tr, .table-row, [class*='row']", "type": "text"},
        {"name": "table_cells", "selector": "td, .table-cell, [class*='cell']", "type": "text"},
        
        # Media and multimedia
        {"name": "images", "selector": "img, .image, [class*='image']", "type": "attribute", "attribute": "alt"},
        {"name": "videos", "selector": "video, .video, [class*='video']", "type": "text"},
        {"name": "audio", "selector": "audio, .audio, [class*='audio']", "type": "text"},
        {"name": "media_captions", "selector": ".caption, .media-caption, [class*='caption']", "type": "text"},
        
        # Business and contact information
        {"name": "contact_info", "selector": ".contact, .contact-info, [class*='contact']", "type": "text"},
        {"name": "address", "selector": ".address, [class*='address']", "type": "text"},
        {"name": "phone", "selector": ".phone, .telephone, [class*='phone'], [class*='tel']", "type": "text"},
        {"name": "email", "selector": ".email, [class*='email'], a[href^='mailto:']", "type": "text"},
        {"name": "social_links", "selector": ".social, .social-links, [class*='social']", "type": "text"},
        
        # Product and service information
        {"name": "products", "selector": ".product, .item, [class*='product'], [class*='item']", "type": "text"},
        {"name": "services", "selector": ".service, [class*='service']", "type": "text"},
        {"name": "features", "selector": ".feature, .features, [class*='feature']", "type": "text"},
        {"name": "benefits", "selector": ".benefit, .benefits, [class*='benefit']", "type": "text"},
        {"name": "specifications", "selector": ".spec, .specs, .specification, [class*='spec']", "type": "text"},
        
        # Pricing and financial (keeping but making optional)
        {"name": "pricing", "selector": ".price, .cost, .pricing, [class*='price'], [class*='cost']", "type": "text"},
        {"name": "currency", "selector": "[class*='currency'], [class*='symbol']", "type": "text"},
        {"name": "financial_info", "selector": "[class*='financial'], [class*='money']", "type": "text"},
        
        # Dates and time
        {"name": "dates", "selector": ".date, .time, [class*='date'], [class*='time']", "type": "text"},
        {"name": "timestamps", "selector": "time, [datetime]", "type": "attribute", "attribute": "datetime"},
        {"name": "events", "selector": ".event, .events, [class*='event']", "type": "text"},
        
        # Categories and tags
        {"name": "categories", "selector": ".category, .categories, [class*='category']", "type": "text"},
        {"name": "tags", "selector": ".tag, .tags, [class*='tag']", "type": "text"},
        {"name": "labels", "selector": ".label, .labels, [class*='label']", "type": "text"},
        
        # Reviews and ratings
        {"name": "reviews", "selector": ".review, .reviews, [class*='review']", "type": "text"},
        {"name": "ratings", "selector": ".rating, .ratings, [class*='rating']", "type": "text"},
        {"name": "testimonials", "selector": ".testimonial, .testimonials, [class*='testimonial']", "type": "text"},
        
        # FAQ and help content
        {"name": "faq", "selector": ".faq, .frequently-asked, [class*='faq']", "type": "text"},
        {"name": "questions", "selector": ".question, .questions, [class*='question']", "type": "text"},
        {"name": "answers", "selector": ".answer, .answers, [class*='answer']", "type": "text"},
        {"name": "help", "selector": ".help, .help-content, [class*='help']", "type": "text"},
        
        # Legal and policy content
        {"name": "terms", "selector": ".terms, .terms-of-service, [class*='terms']", "type": "text"},
        {"name": "privacy", "selector": ".privacy, .privacy-policy, [class*='privacy']", "type": "text"},
        {"name": "legal", "selector": ".legal, .legal-notice, [class*='legal']", "type": "text"},
        
        # Technical information
        {"name": "code", "selector": "code, pre, .code, [class*='code']", "type": "text"},
        {"name": "technical_specs", "selector": ".tech-spec, .technical, [class*='tech'], [class*='technical']", "type": "text"},
        {"name": "documentation", "selector": ".docs, .documentation, [class*='doc']", "type": "text"},
        
        # Meta information
        {"name": "page_title", "selector": "title", "type": "text"},
        {"name": "meta_description", "selector": "meta[name='description']", "type": "attribute", "attribute": "content"},
        {"name": "meta_keywords", "selector": "meta[name='keywords']", "type": "attribute", "attribute": "content"},
        {"name": "canonical_url", "selector": "link[rel='canonical']", "type": "attribute", "attribute": "href"},
        
        # Accessibility and semantic content
        {"name": "alt_text", "selector": "img[alt]", "type": "attribute", "attribute": "alt"},
        {"name": "aria_labels", "selector": "[aria-label]", "type": "attribute", "attribute": "aria-label"},
        {"name": "landmarks", "selector": "[role='main'], [role='navigation'], [role='banner'], [role='contentinfo']", "type": "text"},
        
        # Dynamic content containers
        {"name": "dynamic_content", "selector": ".dynamic, .ajax-content, [class*='dynamic'], [class*='ajax']", "type": "text"},
        {"name": "widgets", "selector": ".widget, .widgets, [class*='widget']", "type": "text"},
        {"name": "components", "selector": ".component, .components, [class*='component']", "type": "text"},
    ]
}

def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "page"

def _domain_slug(url: str) -> str:
    domain = urlparse(url).netloc or "local"
    return _slugify(domain)

def _folder_for(url: str) -> Path:
    folder = MARKDOWN_ROOT / _domain_slug(url)
    folder.mkdir(parents=True, exist_ok=True)  # reuse if exists
    return folder

def _path_name_from_url(url: str) -> str:
    """
    Return a short, meaningful name derived from the URL path.
    Examples:
      https://site.com/about -> "about"
      https://site.com/docs/intro.html -> "intro"
      https://site.com/ -> ""  (no usable name)
    """
    p = urlparse(url)
    segments = [s for s in p.path.split("/") if s]
    if not segments:
        return ""  # root path => no usable name

    leaf = segments[-1]  # last non-empty segment
    # If leaf has an extension, strip it
    leaf_stem = PurePosixPath(leaf).stem

    # Consider default pages as "not meaningful"
    if leaf_stem.lower() in {"index", "home", "default"}:
        return ""

    return leaf_stem

def _filename_for(url: str, title: str | None, folder: Path) -> str:
    # Prefer the name from path; only use title if path gives no name
    base = _path_name_from_url(url) or (title or "").strip() or "index"
    slug = _slugify(base)

    fname = f"{slug}.md"
    path = folder / fname
    if path.exists():
        # Keep it short but unique by adding a tiny hash from the URL
        short_hash = hashlib.blake2s(url.encode("utf-8"), digest_size=3).hexdigest()  # 6 hex chars
        fname = f"{slug}-{short_hash}.md"
    return fname

def _save_markdown(url: str, title: str | None, markdown: str) -> str:
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
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in EXCLUDE_EXTS)

def _same_site(url: str, netloc: str) -> bool:
    p = urlparse(url)
    return not p.netloc or p.netloc == netloc  # allow relative or same host

async def _discover_from_sitemap(root_url: str, max_urls: int) -> List[str]:
    """
    Try fast URL discovery from sitemap.
    Returns a list of URLs (may be empty if no sitemap or nothing useful).
    """
    domain = urlparse(root_url).netloc or root_url
    async with AsyncUrlSeeder() as seeder:
        config = SeedingConfig(
            source="sitemap",     # prefer sitemap
            extract_head=False,   # faster; we just want URLs
            live_check=False,
            max_urls=max_urls,
        )
        urls_meta = await seeder.urls(domain, config)
        return [u["url"] for u in urls_meta if u.get("status") in (None, "valid")]

async def _bfs_internal_links(root_url: str, max_pages: int) -> List[str]:
    """
    Fallback: crawl the root page, pull internal links, and iterate (BFS).
    Only same-domain links are queued.
    """
    parsed = urlparse(root_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    visited: Set[str] = set()
    q: Deque[str] = deque([root_url])
    collected: List[str] = []

    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.1, threshold_type="fixed")  # Minimal filtering
    )
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_gen,
        only_text=False,  # Keep HTML structure
        exclude_all_images=False,  # Keep images for alt text
        score_links=False,
        word_count_threshold=10,  # Very low threshold
        wait_for="networkidle",  # Wait for dynamic content
        delay_before_return_html=2,  # Give time for JavaScript
    )

    async with AsyncWebCrawler() as crawler:
        while q and len(collected) < max_pages:
            url = q.popleft()
            if url in visited or _should_skip(url):
                continue
            visited.add(url)

            res = await crawler.arun(url, config=run_conf)
            if not res.success:
                continue

            collected.append(url)

            # Discover internal links from this page for next iterations
            internal = res.links.get("internal", [])  # provided by Crawl4AI result
            for link in internal:
                href = link.get("href")
                if not href:
                    continue
                abs_url = urljoin(base, href)
                if _same_site(abs_url, parsed.netloc) and abs_url not in visited and not _should_skip(abs_url):
                    q.append(abs_url)

    return collected

async def crawl_site(root_url: str, max_pages: int = 100) -> None:
    """
    Main entry: discover URLs (sitemap first, BFS fallback) and crawl them.
    Prints the page "name" (title if available, else URL path).
    """
    # 1) Discover
    urls = await _discover_from_sitemap(root_url, max_urls=max_pages)
    if not urls:
        urls = await _bfs_internal_links(root_url, max_pages=max_pages)

    print(f"Discovered {len(urls)} URL(s) to crawl")

    # 2) Crawl (Comprehensive configuration for exhaustive content extraction)
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.1, threshold_type="fixed")  # Minimal filtering
    )
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,     # bypass cache for freshness
        markdown_generator=md_gen,
        only_text=False,                 # Keep HTML structure for better extraction
        exclude_all_images=False,        # Keep images for alt text extraction
        word_count_threshold=10,         # Very low threshold to capture all content
        stream=True,                     # stream results as they finish
        wait_for="domcontentloaded",     # Less strict than networkidle
        wait_for_timeout=30000,          # 30 seconds timeout
        page_timeout=60000,              # 60 seconds page timeout
        delay_before_return_html=2,      # Reduced delay
        remove_overlay_elements=True,    # Remove overlays that might hide content
        simulate_user=True,              # Simulate user interaction
    )

    titles: List[str] = []
    async with AsyncWebCrawler() as crawler:
        async for res in await crawler.arun_many(urls, config=run_conf):
            if res.success:
                # Prefer the <title>, fallback to path or URL
                title = (res.metadata or {}).get("title") if isinstance(res.metadata, dict) else None
                name = (title or urlparse(res.url).path or res.url).strip()
                titles.append(name)
                 # NEW: persist markdown to disk
                saved_to = _save_markdown(
                    res.url,
                    title,
                    getattr(res, "markdown", "") or ""  # LLM-friendly content
                )
                print(f"✓ {name}")
            else:
                print(f"✗ {res.url} -> {res.error_message}")

    print(f"\nCrawled {len(titles)} page(s).")

async def crawl_site_with_data(root_url: str, max_pages: int = 100) -> List[PageRaw]:
    """
    Crawl a site and return PageRaw objects with enhanced price/cost extraction.
    """
    from apps.core.types import PageRaw
    
    # 1) Discover URLs
    urls = await _discover_from_sitemap(root_url, max_urls=max_pages)
    if not urls:
        urls = await _bfs_internal_links(root_url, max_pages=max_pages)

    print(f"Discovered {len(urls)} URL(s) to crawl")
    
    # If no URLs discovered, try crawling just the root URL
    if not urls:
        print("No URLs discovered, trying to crawl root URL directly")
        urls = [root_url]

    # 2) Comprehensive crawling configuration for exhaustive information capture
    # Minimal content filtering to preserve all information
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.1, threshold_type="fixed")  # Very minimal filtering
    )
    
    # Create comprehensive extraction strategy for all types of content
    comprehensive_extraction = JsonCssExtractionStrategy(COMPREHENSIVE_EXTRACTION_SCHEMA)
    
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_gen,
        extraction_strategy=comprehensive_extraction,  # Comprehensive structured extraction
        only_text=False,  # Keep HTML structure for better extraction
        exclude_all_images=False,  # Keep images for alt text extraction
        word_count_threshold=10,  # Very low threshold to capture all content
        stream=True,
        # More robust waiting strategy
        wait_for="domcontentloaded",  # Less strict than networkidle
        wait_for_timeout=30000,  # 30 seconds timeout
        page_timeout=60000,  # 60 seconds page timeout
        delay_before_return_html=2,  # Reduced delay
        # Additional options for comprehensive crawling
        remove_overlay_elements=True,  # Remove overlays that might hide content
        simulate_user=True,  # Simulate user interaction
        js_code="window.scrollTo(0, document.body.scrollHeight);",  # Scroll to load lazy content
    )

    pages = []
    success_count = 0
    
    # Try comprehensive crawling first
    print(f"DEBUG: Starting comprehensive crawl with {len(urls)} URLs")
    async with AsyncWebCrawler() as crawler:
        async for res in await crawler.arun_many(urls, config=run_conf):
            if res.success:
                success_count += 1
                title = (res.metadata or {}).get("title") if isinstance(res.metadata, dict) else None
                content = getattr(res, "markdown", "") or ""
                
                # Extract comprehensive structured data
                extracted_data = {}
                if hasattr(res, 'extracted_content') and res.extracted_content:
                    extracted_data = res.extracted_content
                
                # Combine markdown content with extracted structured data
                enhanced_content = content
                if extracted_data:
                    # Add extracted information to content in organized sections
                    info_sections = {}
                    
                    # Categorize extracted data
                    for field_name, field_value in extracted_data.items():
                        if field_value and isinstance(field_value, (str, list)) and str(field_value).strip():
                            # Clean and format the value
                            if isinstance(field_value, list):
                                clean_value = " | ".join([str(v).strip() for v in field_value if str(v).strip()])
                            else:
                                clean_value = str(field_value).strip()
                            
                            if clean_value:
                                # Categorize by field type
                                if field_name in ['main_title', 'subtitle', 'headings']:
                                    info_sections.setdefault('Titles and Headings', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['paragraphs', 'main_content', 'articles', 'sections']:
                                    info_sections.setdefault('Main Content', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['products', 'services', 'features', 'benefits', 'specifications']:
                                    info_sections.setdefault('Products and Services', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['pricing', 'currency', 'financial_info']:
                                    info_sections.setdefault('Pricing Information', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['contact_info', 'address', 'phone', 'email', 'social_links']:
                                    info_sections.setdefault('Contact Information', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['faq', 'questions', 'answers', 'help']:
                                    info_sections.setdefault('FAQ and Help', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['reviews', 'ratings', 'testimonials']:
                                    info_sections.setdefault('Reviews and Testimonials', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                elif field_name in ['tables', 'table_headers', 'table_rows', 'table_cells']:
                                    info_sections.setdefault('Structured Data', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                                else:
                                    info_sections.setdefault('Other Information', []).append(f"{field_name.replace('_', ' ').title()}: {clean_value}")
                    
                    # Add organized sections to content
                    if info_sections:
                        enhanced_content += "\n\n## Extracted Structured Information\n"
                        for section_name, items in info_sections.items():
                            if items:
                                enhanced_content += f"\n### {section_name}\n"
                                for item in items[:10]:  # Limit to prevent overwhelming content
                                    enhanced_content += f"- {item}\n"
                                if len(items) > 10:
                                    enhanced_content += f"- ... and {len(items) - 10} more items\n"
                
                # Create PageRaw object with comprehensive metadata
                page = PageRaw(
                    content_id=f"crawl_{hashlib.md5(res.url.encode()).hexdigest()[:8]}",
                    url=res.url,
                    title=title or urlparse(res.url).path or res.url,
                    content=enhanced_content,
                    metadata={
                        "crawled_at": datetime.now().isoformat(),
                        "word_count": len(enhanced_content.split()) if enhanced_content else 0,
                        "source": "crawl4ai_comprehensive",
                        "extracted_data": extracted_data,  # Store all structured data
                        "extraction_stats": {
                            "total_fields_extracted": len([k for k, v in extracted_data.items() if v]),
                            "has_content": bool(extracted_data.get('main_content') or extracted_data.get('paragraphs')),
                            "has_products": bool(extracted_data.get('products') or extracted_data.get('services')),
                            "has_pricing": bool(extracted_data.get('pricing') or extracted_data.get('financial_info')),
                            "has_contact": bool(extracted_data.get('contact_info') or extracted_data.get('email')),
                            "has_faq": bool(extracted_data.get('faq') or extracted_data.get('questions')),
                            "has_reviews": bool(extracted_data.get('reviews') or extracted_data.get('testimonials')),
                            "has_tables": bool(extracted_data.get('tables')),
                        },
                        "content_types": [k for k, v in extracted_data.items() if v and k not in ['page_title', 'meta_description']]
                    }
                )
                pages.append(page)
                
                # Enhanced status display
                stats = page.metadata['extraction_stats']
                status_icons = []
                if stats['has_content']: status_icons.append('📄')
                if stats['has_products']: status_icons.append('🛍️')
                if stats['has_pricing']: status_icons.append('💰')
                if stats['has_contact']: status_icons.append('📞')
                if stats['has_faq']: status_icons.append('❓')
                if stats['has_reviews']: status_icons.append('⭐')
                if stats['has_tables']: status_icons.append('📊')
                
                print(f"✓ {page.title} {' '.join(status_icons)} ({stats['total_fields_extracted']} fields)")
            else:
                print(f"✗ {res.url} -> {res.error_message}")
    
    # If no pages were successfully crawled, try fallback strategies
    if success_count == 0:
        print(f"No pages crawled successfully, trying fallback strategies...")
        
        # Try fallback with minimal configuration
        print("Trying fallback crawling with minimal configuration...")
        fallback_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=md_gen,
            only_text=True,  # Simplified
            word_count_threshold=1,
            wait_until="load",  # Most basic wait condition
            page_timeout=15000,  # 15 seconds
            delay_before_return_html=0.5,  # Minimal delay
            ignore_body_visibility=True,  # Don't wait for body visibility
        )
        
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(urls, config=fallback_config)
            for res in results:
                if res.success:
                    success_count += 1
                    title = (res.metadata or {}).get("title") if isinstance(res.metadata, dict) else None
                    content = getattr(res, "markdown", "") or ""
                    
                    page = PageRaw(
                        content_id=f"crawl_{hashlib.md5(res.url.encode()).hexdigest()[:8]}",
                        url=res.url,
                        title=title or urlparse(res.url).path or res.url,
                        content=content,
                        metadata={
                            "crawled_at": datetime.now().isoformat(),
                            "word_count": len(content.split()) if content else 0,
                            "source": "crawl4ai_fallback",
                            "extracted_data": {},
                            "extraction_stats": {
                                "total_fields_extracted": 0,
                                "has_content": bool(content),
                                "has_products": False,
                                "has_pricing": False,
                                "has_contact": False,
                                "has_faq": False,
                                "has_reviews": False,
                                "has_tables": False,
                            },
                            "content_types": []
                        }
                    )
                    pages.append(page)
                    print(f"✓ {page.title} (fallback)")
                else:
                    print(f"✗ {res.url} -> {res.error_message}")
        
        # If still no success, try ultra-minimal configuration
        if success_count == 0:
            print("Trying ultra-minimal crawling...")
            ultra_minimal_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                only_text=True,
                word_count_threshold=1,
                page_timeout=10000,  # 10 seconds
                delay_before_return_html=0.1,  # Very minimal delay
                ignore_body_visibility=True,
                wait_until="domcontentloaded",  # Basic wait
            )
            
            async with AsyncWebCrawler() as crawler:
                results = await crawler.arun_many(urls, config=ultra_minimal_config)
                for res in results:
                    if res.success:
                        success_count += 1
                        title = (res.metadata or {}).get("title") if isinstance(res.metadata, dict) else None
                        content = getattr(res, "markdown", "") or ""
                        
                        page = PageRaw(
                            content_id=f"crawl_{hashlib.md5(res.url.encode()).hexdigest()[:8]}",
                            url=res.url,
                            title=title or urlparse(res.url).path or res.url,
                            content=content,
                            metadata={
                                "crawled_at": datetime.now().isoformat(),
                                "word_count": len(content.split()) if content else 0,
                                "source": "crawl4ai_ultra_minimal",
                                "extracted_data": {},
                                "extraction_stats": {
                                    "total_fields_extracted": 0,
                                    "has_content": bool(content),
                                    "has_products": False,
                                    "has_pricing": False,
                                    "has_contact": False,
                                    "has_faq": False,
                                    "has_reviews": False,
                                    "has_tables": False,
                                },
                                "content_types": []
                            }
                        )
                        pages.append(page)
                        print(f"✓ {page.title} (ultra-minimal)")
                    else:
                        print(f"✗ {res.url} -> {res.error_message}")
            
            # If still no success, create a placeholder page
            if success_count == 0:
                print("Creating basic page with URL only...")
                page = PageRaw(
                    content_id=f"crawl_{hashlib.md5(root_url.encode()).hexdigest()[:8]}",
                    url=root_url,
                    title=urlparse(root_url).path or root_url,
                    content=f"Failed to crawl {root_url}. This page could not be processed due to technical issues.",
                    metadata={
                        "crawled_at": datetime.now().isoformat(),
                        "word_count": 0,
                        "source": "crawl4ai_failed",
                        "extracted_data": {},
                        "extraction_stats": {
                            "total_fields_extracted": 0,
                            "has_content": False,
                            "has_products": False,
                            "has_pricing": False,
                            "has_contact": False,
                            "has_faq": False,
                            "has_reviews": False,
                            "has_tables": False,
                        },
                        "content_types": []
                    }
                )
                pages.append(page)
                print(f"✓ {page.title} (failed crawl placeholder)")

    print(f"\nCrawled {len(pages)} page(s).")
    return pages

async def test_comprehensive_extraction(url: str) -> None:
    """
    Test function to demonstrate comprehensive information extraction.
    """
    print(f"Testing comprehensive extraction on: {url}")
    pages = await crawl_site_with_data(url, max_pages=1)
    
    if pages:
        page = pages[0]
        print(f"\n=== COMPREHENSIVE EXTRACTION RESULTS ===")
        print(f"Title: {page.title}")
        print(f"URL: {page.url}")
        print(f"Word Count: {page.metadata.get('word_count', 0)}")
        
        stats = page.metadata.get('extraction_stats', {})
        print(f"\n=== EXTRACTION STATISTICS ===")
        print(f"Total Fields Extracted: {stats.get('total_fields_extracted', 0)}")
        print(f"Content Types Found: {', '.join(page.metadata.get('content_types', []))}")
        
        print(f"\n=== CONTENT TYPE BREAKDOWN ===")
        content_icons = {
            'has_content': '📄 Main Content',
            'has_products': '🛍️ Products/Services', 
            'has_pricing': '💰 Pricing Info',
            'has_contact': '📞 Contact Info',
            'has_faq': '❓ FAQ/Help',
            'has_reviews': '⭐ Reviews',
            'has_tables': '📊 Structured Data'
        }
        
        for key, label in content_icons.items():
            status = "✓" if stats.get(key, False) else "✗"
            print(f"{status} {label}")
        
        if page.metadata.get('extracted_data'):
            print(f"\n=== SAMPLE EXTRACTED DATA ===")
            # Show sample of each content type
            sample_data = {}
            for key, value in page.metadata['extracted_data'].items():
                if value and key not in ['page_title', 'meta_description']:
                    if isinstance(value, list):
                        sample_data[key] = value[:3]  # First 3 items
                    else:
                        sample_data[key] = str(value)[:100]  # First 100 chars
            
            for key, value in list(sample_data.items())[:10]:  # Show first 10 fields
                print(f"{key}: {value}")
            
            if len(sample_data) > 10:
                print(f"... and {len(sample_data) - 10} more fields")
        
        print(f"\n=== ENHANCED CONTENT PREVIEW ===")
        print(page.content[:800] + "..." if len(page.content) > 800 else page.content)
    else:
        print("No pages were successfully crawled.")

if __name__ == "__main__":
    # CLI usage:
    #   python -m knowledgeinjester.crawler.simple_crawl4ai https://example.com 100
    import sys
    import asyncio
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        
        if "--test-comprehensive" in sys.argv:
            # Test comprehensive extraction on a single page
            asyncio.run(test_comprehensive_extraction(url))
        else:
            # Regular comprehensive crawling
            asyncio.run(crawl_site_with_data(url, max_pages))
    else:
        print("Usage: python -m apps.crawler.simple_crawl4ai <url> [max_pages] [--test-comprehensive]")
        print("Example: python -m apps.crawler.simple_crawl4ai https://example.com 10 --test-comprehensive")
        print("\nThis crawler now performs comprehensive extraction of all types of content including:")
        print("- Main content, headings, paragraphs")
        print("- Products, services, features, benefits")
        print("- Pricing and financial information")
        print("- Contact information and business details")
        print("- FAQ, help content, and documentation")
        print("- Reviews, testimonials, and ratings")
        print("- Tables and structured data")
        print("- Navigation, forms, and interactive elements")
