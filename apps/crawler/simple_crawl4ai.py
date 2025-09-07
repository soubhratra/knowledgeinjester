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

# NEW: where to store local markdown files
MARKDOWN_ROOT = Path(__file__).parent / "markdown"

# Skip obvious non-HTML assets
EXCLUDE_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".gz",
    ".mp4", ".webm", ".css", ".js", ".ico", ".woff", ".woff2",
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
        content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
    )
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_gen,
        only_text=True,
        exclude_all_images=True,
        score_links=False,
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

    # 2) Crawl (Markdown generator -> LLM-friendly text available if you want to persist)
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
    )
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,     # bypass cache for freshness
        markdown_generator=md_gen,
        only_text=True,
        exclude_all_images=True,
        word_count_threshold=50,         # skip tiny pages
        stream=True,                     # stream results as they finish
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
    Crawl a site and return PageRaw objects instead of just saving to disk.
    """
    from apps.core.types import PageRaw
    
    # 1) Discover URLs
    urls = await _discover_from_sitemap(root_url, max_urls=max_pages)
    if not urls:
        urls = await _bfs_internal_links(root_url, max_pages=max_pages)

    print(f"Discovered {len(urls)} URL(s) to crawl")

    # 2) Crawl and collect data
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed")
    )
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_gen,
        only_text=True,
        exclude_all_images=True,
        word_count_threshold=50,
        stream=True,
    )

    pages = []
    async with AsyncWebCrawler() as crawler:
        async for res in await crawler.arun_many(urls, config=run_conf):
            if res.success:
                title = (res.metadata or {}).get("title") if isinstance(res.metadata, dict) else None
                content = getattr(res, "markdown", "") or ""
                
                # Create PageRaw object
                page = PageRaw(
                    content_id=f"crawl_{hashlib.md5(res.url.encode()).hexdigest()[:8]}",
                    url=res.url,
                    title=title or urlparse(res.url).path or res.url,
                    content=content,
                    metadata={
                        "crawled_at": datetime.now().isoformat(),
                        "word_count": len(content.split()) if content else 0,
                        "source": "crawl4ai"
                    }
                )
                pages.append(page)
                print(f"✓ {page.title}")
            else:
                print(f"✗ {res.url} -> {res.error_message}")

    print(f"\nCrawled {len(pages)} page(s).")
    return pages

if __name__ == "__main__":
    # CLI usage:
    #   python -m knowledgeinjester.crawler.simple_crawl4ai https://example.com 100
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m knowledgeinjester.crawler.simple_crawl4ai <root_url> [max_pages]")
        raise SystemExit(2)
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(crawl_site(url, max_pages))
