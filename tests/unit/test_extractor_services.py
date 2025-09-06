"""
Unit tests for extractor services.
"""
import pytest
from unittest.mock import patch
from apps.extractor.services import extract_markdown
from apps.core.types import PageRaw, Doc


class TestExtractorServices:
    """Test extractor service functions."""
    
    def test_extract_markdown_success(self, sample_page_raw):
        """Test successful markdown extraction."""
        pages = [sample_page_raw]
        
        result = extract_markdown(pages)
        
        assert len(result) == 1
        assert isinstance(result[0], Doc)
        assert result[0].content_id == sample_page_raw.content_id
        assert result[0].url == sample_page_raw.url
        assert result[0].title == sample_page_raw.title
        assert result[0].content == sample_page_raw.content
        assert result[0].markdown == sample_page_raw.content  # Simplified for now
    
    def test_extract_markdown_multiple_pages(self):
        """Test markdown extraction with multiple pages."""
        pages = [
            PageRaw(
                url="https://example.com/page1",
                title="Page 1",
                content="Content 1",
                metadata={"status": 200}
            ),
            PageRaw(
                url="https://example.com/page2",
                title="Page 2",
                content="Content 2",
                metadata={"status": 200}
            )
        ]
        
        result = extract_markdown(pages)
        
        assert len(result) == 2
        assert all(isinstance(doc, Doc) for doc in result)
        assert result[0].title == "Page 1"
        assert result[1].title == "Page 2"
    
    def test_extract_markdown_empty_list(self):
        """Test markdown extraction with empty page list."""
        result = extract_markdown([])
        
        assert result == []
    
    def test_extract_markdown_with_failure(self):
        """Test markdown extraction with some failures."""
        pages = [
            PageRaw(
                url="https://example.com/good",
                title="Good Page",
                content="Good content",
                metadata={"status": 200}
            ),
            PageRaw(
                url="https://example.com/bad",
                title="Bad Page",
                content="Bad content",
                metadata={"status": 404}
            )
        ]
        
        # Mock the extraction to fail for the second page
        with patch('apps.extractor.services.Doc') as mock_doc:
            mock_doc.side_effect = [Doc(
                content_id=pages[0].content_id,
                url=pages[0].url,
                title=pages[0].title,
                content=pages[0].content,
                markdown=pages[0].content,
                metadata=pages[0].metadata
            ), Exception("Extraction failed")]
            
            result = extract_markdown(pages)
            
            # Should only return the successful extraction
            assert len(result) == 1
            assert result[0].title == "Good Page"

