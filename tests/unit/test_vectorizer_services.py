"""
Unit tests for vectorizer services.
"""
import pytest
from apps.vectorizer.services import vectorize_docs
from apps.core.types import Doc, UpsertSummary


class TestVectorizerServices:
    """Test vectorizer service functions."""
    
    def test_vectorize_docs_success(self, sample_doc):
        """Test successful document vectorization."""
        docs = [sample_doc]
        
        result = vectorize_docs(docs)
        
        assert isinstance(result, UpsertSummary)
        assert result.total_chunks == 0  # Placeholder implementation
        assert result.successful_upserts == 0
        assert result.failed_upserts == 0
        assert result.skipped_duplicates == 0
        assert result.processing_time_seconds == 0.0
    
    def test_vectorize_docs_multiple_docs(self):
        """Test vectorization with multiple documents."""
        docs = [
            Doc(
                content_id="doc1",
                url="https://example.com/doc1",
                title="Document 1",
                content="Content 1",
                markdown="# Document 1\n\nContent 1"
            ),
            Doc(
                content_id="doc2",
                url="https://example.com/doc2",
                title="Document 2",
                content="Content 2",
                markdown="# Document 2\n\nContent 2"
            )
        ]
        
        result = vectorize_docs(docs)
        
        assert isinstance(result, UpsertSummary)
        assert result.total_chunks == 0  # Placeholder implementation
    
    def test_vectorize_docs_empty_list(self):
        """Test vectorization with empty document list."""
        result = vectorize_docs([])
        
        assert isinstance(result, UpsertSummary)
        assert result.total_chunks == 0


