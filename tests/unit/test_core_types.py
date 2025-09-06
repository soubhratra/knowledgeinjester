"""
Unit tests for core type definitions.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from apps.core.types import (
    PageRaw, Doc, Chunk, Embedding, UpsertSummary,
    CrawlJob, IngestJob, IngestRequest, IngestResponse
)


class TestPageRaw:
    """Test PageRaw model."""
    
    def test_page_raw_creation(self):
        """Test creating a PageRaw object."""
        page = PageRaw(
            url="https://example.com",
            title="Test Page",
            content="Test content",
            metadata={"status": 200}
        )
        
        assert str(page.url) == "https://example.com/"
        assert page.title == "Test Page"
        assert page.content == "Test content"
        assert page.metadata == {"status": 200}
        assert isinstance(page.crawled_at, datetime)
    
    def test_page_raw_domain_property(self):
        """Test domain property extraction."""
        page = PageRaw(url="https://example.com", content="test")
        assert page.domain == "example.com"
    
    def test_page_raw_content_id_property(self):
        """Test content ID property."""
        page = PageRaw(url="https://example.com", content="test content")
        content_id = page.content_id
        assert isinstance(content_id, str)
        assert len(content_id) == 64  # SHA256 hash length


class TestDoc:
    """Test Doc model."""
    
    def test_doc_creation(self):
        """Test creating a Doc object."""
        doc = Doc(
            content_id="test-id",
            url="https://example.com",
            title="Test Doc",
            content="Test content",
            markdown="# Test Doc\n\nTest content"
        )
        
        assert doc.content_id == "test-id"
        assert str(doc.url) == "https://example.com/"
        assert doc.title == "Test Doc"
        assert doc.content == "Test content"
        assert doc.markdown == "# Test Doc\n\nTest content"
        assert isinstance(doc.processed_at, datetime)
    
    def test_doc_domain_property(self):
        """Test domain property extraction."""
        doc = Doc(
            content_id="test-id",
            url="https://example.com",
            content="test",
            markdown="test"
        )
        assert doc.domain == "example.com"


class TestChunk:
    """Test Chunk model."""
    
    def test_chunk_creation(self):
        """Test creating a Chunk object."""
        chunk = Chunk(
            chunk_id="chunk-123",
            content_id="content-123",
            content="Test chunk content",
            chunk_index=0,
            total_chunks=5
        )
        
        assert chunk.chunk_id == "chunk-123"
        assert chunk.content_id == "content-123"
        assert chunk.content == "Test chunk content"
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 5
    
    def test_chunk_validation_negative_index(self):
        """Test chunk validation with negative index."""
        with pytest.raises(ValidationError):
            Chunk(
                chunk_id="chunk-123",
                content_id="content-123",
                content="test",
                chunk_index=-1,
                total_chunks=5
            )
    
    def test_chunk_validation_zero_total(self):
        """Test chunk validation with zero total chunks."""
        with pytest.raises(ValidationError):
            Chunk(
                chunk_id="chunk-123",
                content_id="content-123",
                content="test",
                chunk_index=0,
                total_chunks=0
            )


class TestEmbedding:
    """Test Embedding model."""
    
    def test_embedding_creation(self):
        """Test creating an Embedding object."""
        embedding = Embedding(
            chunk_id="chunk-123",
            content_id="content-123",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100-dimensional vector
            model="test-model"
        )
        
        assert embedding.chunk_id == "chunk-123"
        assert embedding.content_id == "content-123"
        assert len(embedding.embedding) == 100
        assert embedding.model == "test-model"
        assert isinstance(embedding.created_at, datetime)
    
    def test_embedding_validation_short_vector(self):
        """Test embedding validation with short vector."""
        with pytest.raises(ValidationError):
            Embedding(
                chunk_id="chunk-123",
                content_id="content-123",
                embedding=[0.1, 0.2],  # Too short
                model="test-model"
            )


class TestUpsertSummary:
    """Test UpsertSummary model."""
    
    def test_upsert_summary_creation(self):
        """Test creating an UpsertSummary object."""
        summary = UpsertSummary(
            total_chunks=100,
            successful_upserts=95,
            failed_upserts=3,
            skipped_duplicates=2,
            processing_time_seconds=10.5
        )
        
        assert summary.total_chunks == 100
        assert summary.successful_upserts == 95
        assert summary.failed_upserts == 3
        assert summary.skipped_duplicates == 2
        assert summary.processing_time_seconds == 10.5
        assert summary.success_rate == 0.95
    
    def test_upsert_summary_zero_total(self):
        """Test success rate with zero total chunks."""
        summary = UpsertSummary(
            total_chunks=0,
            successful_upserts=0,
            failed_upserts=0,
            skipped_duplicates=0,
            processing_time_seconds=0.0
        )
        
        assert summary.success_rate == 0.0


class TestCrawlJob:
    """Test CrawlJob model."""
    
    def test_crawl_job_creation(self):
        """Test creating a CrawlJob object."""
        job = CrawlJob(
            job_id="job-123",
            root_url="https://example.com",
            max_pages=50
        )
        
        assert job.job_id == "job-123"
        assert str(job.root_url) == "https://example.com/"
        assert job.max_pages == 50
        assert job.status == "pending"
        assert isinstance(job.created_at, datetime)


class TestIngestRequest:
    """Test IngestRequest model."""
    
    def test_ingest_request_creation(self):
        """Test creating an IngestRequest object."""
        request = IngestRequest(
            root_url="https://example.com",
            tenant_id="tenant-123",
            max_pages=100
        )
        
        assert str(request.root_url) == "https://example.com/"
        assert request.tenant_id == "tenant-123"
        assert request.max_pages == 100
        assert request.crawl_config == {}
        assert request.extract_config == {}
        assert request.vectorize_config == {}
    
    def test_ingest_request_validation_max_pages(self):
        """Test max_pages validation."""
        with pytest.raises(ValidationError):
            IngestRequest(
                root_url="https://example.com",
                max_pages=0  # Should be >= 1
            )
        
        with pytest.raises(ValidationError):
            IngestRequest(
                root_url="https://example.com",
                max_pages=2000  # Should be <= 1000
            )

