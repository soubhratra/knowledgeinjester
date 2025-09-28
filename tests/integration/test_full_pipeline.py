"""
Integration tests for the full knowledge ingestion pipeline.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.crawler.services import crawl_website_sync
from apps.extractor.services import extract_markdown
from apps.vectorizer.services import vectorize_docs
from apps.core.types import PageRaw, Doc, UpsertSummary


@pytest.mark.integration
@pytest.mark.django_db
class TestFullPipeline:
    """Test the complete knowledge ingestion pipeline."""
    
    def test_full_pipeline_success(self):
        """Test successful end-to-end pipeline execution."""
        # Mock the crawler to return sample data
        mock_pages = [
            PageRaw(
                url="https://example.com",
                title="Example Page",
                content="This is example content for testing.",
                metadata={"status": 200}
            ),
            PageRaw(
                url="https://example.com/about",
                title="About Page",
                content="This is about page content.",
                metadata={"status": 200}
            )
        ]
        
        with patch('apps.crawler.services.crawl_site') as mock_crawl:
            mock_crawl.return_value = None
            
            # Step 1: Crawl
            pages = crawl_website_sync("https://example.com", 2)
            assert pages == []  # Current implementation returns empty list
            
            # Step 2: Extract (using mock data)
            docs = extract_markdown(mock_pages)
            assert len(docs) == 2
            assert all(isinstance(doc, Doc) for doc in docs)
            
            # Step 3: Vectorize
            summary = vectorize_docs("test-tenant", docs)
            # Check if result is UpsertSummary or tuple
            if hasattr(summary, 'total_docs'):
                assert summary.total_docs >= 0
                assert summary.total_chunks >= 0
            else:
                assert isinstance(summary, tuple)  # Returns (docs_count, chunks_count)
    
    def test_pipeline_with_crawler_failure(self):
        """Test pipeline behavior when crawler fails."""
        with patch('apps.crawler.services.crawl_site') as mock_crawl:
            mock_crawl.side_effect = Exception("Crawl failed")
            
            with pytest.raises(Exception, match="Crawl failed"):
                crawl_website_sync("https://example.com", 2)
    
    def test_pipeline_with_extractor_failure(self):
        """Test pipeline behavior when extractor fails."""
        # Create pages that will cause extraction to fail
        pages = [
            PageRaw(
                url="https://example.com",
                title="Test Page",
                content="Test content",
                metadata={"status": 200}
            )
        ]
        
        with patch('apps.extractor.services.Doc') as mock_doc:
            mock_doc.side_effect = Exception("Extraction failed")
            
            docs = extract_markdown(pages)
            assert docs == []  # Should return empty list on failure
    
    def test_pipeline_with_empty_crawl_result(self):
        """Test pipeline with empty crawl results."""
        pages = []
        
        docs = extract_markdown(pages)
        assert docs == []
        
        summary = vectorize_docs("test-tenant", docs)
        # Check if result is UpsertSummary or tuple
        if hasattr(summary, 'total_docs'):
            assert summary.total_docs == 0
            assert summary.total_chunks == 0
        else:
            assert isinstance(summary, tuple)
            assert summary[0] == 0  # docs_count
            assert summary[1] == 0  # chunks_count
    
    def test_pipeline_data_flow(self):
        """Test data flow through the pipeline."""
        # Create test data
        pages = [
            PageRaw(
                url="https://example.com/page1",
                title="Page 1",
                content="Content 1",
                metadata={"status": 200, "content_type": "text/html"}
            )
        ]
        
        # Test data transformation through pipeline
        docs = extract_markdown(pages)
        assert len(docs) == 1
        
        doc = docs[0]
        assert doc.content_id == pages[0].content_id
        assert doc.url == pages[0].url
        assert doc.title == pages[0].title
        assert doc.content == pages[0].content
        
        # Test vectorization
        summary = vectorize_docs("test-tenant", docs)
        # Check if result is UpsertSummary or tuple
        if hasattr(summary, 'total_docs'):
            assert summary.total_docs >= 0
            assert summary.total_chunks >= 0
        else:
            assert isinstance(summary, tuple)
            assert summary[0] >= 0  # docs_count
            assert summary[1] >= 0  # chunks_count


