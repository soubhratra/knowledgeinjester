# Crawler Django app
# Lazy import to avoid startup issues
def crawl_site(*args, **kwargs):
    from .simple_crawl4ai import crawl_site as _crawl_site
    return _crawl_site(*args, **kwargs)

__all__ = ["crawl_site"]
