"""
Pytest configuration and shared fixtures.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator

import pytest
import django
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

# Ensure Django is configured before importing models
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.test_settings')
    django.setup()

from apps.tenants.models import Organization, DataSource, CrawlJob, IngestJob
from apps.core.types import PageRaw, Doc, Chunk


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup database for the entire test session."""
    with django_db_blocker.unblock():
        # Create test data here if needed
        pass


@pytest.fixture
def temp_markdown_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for markdown files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_organization() -> Organization:
    """Create a test organization."""
    return Organization.objects.create(
        name="Test Organization",
        slug="test-org",
        tenant_id="test-tenant-123",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_key="test-service-key"
    )


@pytest.fixture
def test_data_source(test_organization: Organization) -> DataSource:
    """Create a test data source."""
    return DataSource.objects.create(
        tenant=test_organization,
        name="Test Website",
        source_type="website",
        config={"url": "https://example.com"}
    )


@pytest.fixture
def test_crawl_job(test_organization: Organization, test_data_source: DataSource) -> CrawlJob:
    """Create a test crawl job."""
    return CrawlJob.objects.create(
        job_id="test-job-123",
        organization=test_organization,
        data_source=test_data_source,
        root_url="https://example.com",
        max_pages=5
    )


@pytest.fixture
def test_ingest_job(test_organization: Organization) -> IngestJob:
    """Create a test ingest job."""
    return IngestJob.objects.create(
        job_id="test-ingest-123",
        organization=test_organization,
        root_url="https://example.com",
        max_pages=5
    )


@pytest.fixture
def sample_page_raw() -> PageRaw:
    """Create a sample PageRaw object."""
    return PageRaw(
        url="https://example.com",
        title="Example Page",
        content="This is example content for testing.",
        metadata={"status": 200, "content_type": "text/html"}
    )


@pytest.fixture
def sample_doc(sample_page_raw: PageRaw) -> Doc:
    """Create a sample Doc object."""
    return Doc(
        content_id=sample_page_raw.content_id,
        url=sample_page_raw.url,
        title=sample_page_raw.title,
        content=sample_page_raw.content,
        markdown="# Example Page\n\nThis is example content for testing.",
        metadata=sample_page_raw.metadata
    )


@pytest.fixture
def sample_chunk(sample_doc: Doc) -> Chunk:
    """Create a sample Chunk object."""
    return Chunk(
        chunk_id="chunk-123",
        content_id=sample_doc.content_id,
        content="This is a test chunk.",
        chunk_index=0,
        total_chunks=1,
        metadata={"source": "test"}
    )


@pytest.fixture
def api_client() -> Client:
    """Create a test API client."""
    return Client()


@pytest.fixture
def authenticated_user() -> User:
    """Create an authenticated user for testing."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    return user


class BaseTestCase(TestCase):
    """Base test case with common utilities."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        self.data_source = DataSource.objects.create(
            tenant=self.organization,
            name="Test Website",
            source_type="website",
            config={"url": "https://example.com"}
        )
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up any temporary files
        pass

