"""
Unit tests for crawler services.
"""
import pytest
from unittest.mock import patch, AsyncMock

from apps.crawler.services import crawl_website, crawl_website_sync
from apps.core.types import PageRaw


class TestCrawlerServices:
    """Test crawler service functions."""
    
    @pytest.mark.asyncio
    async def test_crawl_website_success(self):
        """Test successful website crawling."""
        with patch('apps.crawler.services.crawl_site') as mock_crawl:
            mock_crawl.return_value = None
            
            result = await crawl_website("https://example.com", 5)
            
            mock_crawl.assert_called_once_with("https://example.com", 5)
            assert result == []
    
    @pytest.mark.asyncio
    async def test_crawl_website_with_tenant(self):
        """Test website crawling with tenant ID."""
        with patch('apps.crawler.services.crawl_site') as mock_crawl:
            mock_crawl.return_value = None
            
            result = await crawl_website("https://example.com", 5, "tenant-123")
            
            mock_crawl.assert_called_once_with("https://example.com", 5)
            assert result == []
    
    @pytest.mark.asyncio
    async def test_crawl_website_failure(self):
        """Test website crawling failure."""
        with patch('apps.crawler.services.crawl_site') as mock_crawl:
            mock_crawl.side_effect = Exception("Crawl failed")
            
            with pytest.raises(Exception, match="Crawl failed"):
                await crawl_website("https://example.com", 5)
    
    def test_crawl_website_sync(self):
        """Test synchronous wrapper."""
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = []
            
            result = crawl_website_sync("https://example.com", 5)
            
            mock_run.assert_called_once()
            assert result == []


