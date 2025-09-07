"""
Integration tests for database models.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.tenants.models import Organization, DataSource, CrawlJob, IngestJob


@pytest.mark.django_db
class TestDatabaseModels:
    """Test database model integration."""
    
    def test_organization_creation(self):
        """Test creating an organization."""
        org = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            tenant_id="test-tenant-123",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="test-anon-key",
            supabase_service_key="test-service-key"
        )
        
        assert org.name == "Test Organization"
        assert org.slug == "test-org"
        assert org.tenant_id == "test-tenant-123"
        assert org.supabase_url == "https://test.supabase.co"
        assert str(org) == "Test Organization"
    
    def test_organization_unique_slug(self):
        """Test organization slug uniqueness."""
        Organization.objects.create(
            name="First Org",
            slug="test-org",
            tenant_id="tenant-1"
        )
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            Organization.objects.create(
                name="Second Org",
                slug="test-org",  # Duplicate slug
                tenant_id="tenant-2"
            )
    
    def test_data_source_creation(self, test_organization):
        """Test creating a data source."""
        source = DataSource.objects.create(
            tenant=test_organization,
            name="Test Website",
            source_type="website",
            config={"url": "https://example.com", "max_pages": 100}
        )
        
        assert source.tenant == test_organization
        assert source.name == "Test Website"
        assert source.source_type == "website"
        assert source.config == {"url": "https://example.com", "max_pages": 100}
        assert source.active is True
        assert str(source) == "Test Organization - Test Website"
    
    def test_data_source_unique_name_per_organization(self, test_organization):
        """Test data source name uniqueness per organization."""
        DataSource.objects.create(
            tenant=test_organization,
            name="Test Source",
            source_type="website"
        )
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            DataSource.objects.create(
                tenant=test_organization,
                name="Test Source",  # Duplicate name
                source_type="api"
            )
    
    def test_crawl_job_creation(self, test_organization, test_data_source):
        """Test creating a crawl job."""
        job = CrawlJob.objects.create(
            job_id="test-job-123",
            organization=test_organization,
            data_source=test_data_source,
            root_url="https://example.com",
            max_pages=50,
            config={"follow_redirects": True}
        )
        
        assert job.job_id == "test-job-123"
        assert job.organization == test_organization
        assert job.data_source == test_data_source
        assert job.root_url == "https://example.com"
        assert job.max_pages == 50
        assert job.status == "pending"
        assert job.config == {"follow_redirects": True}
        assert str(job) == "test-job-123 - https://example.com"
    
    def test_ingest_job_creation(self, test_organization):
        """Test creating an ingest job."""
        job = IngestJob.objects.create(
            job_id="test-ingest-123",
            organization=test_organization,
            root_url="https://example.com",
            max_pages=100,
            crawl_config={"max_pages": 100},
            extract_config={"clean_html": True},
            vectorize_config={"chunk_size": 1000}
        )
        
        assert job.job_id == "test-ingest-123"
        assert job.organization == test_organization
        assert job.root_url == "https://example.com"
        assert job.max_pages == 100
        assert job.status == "pending"
        assert job.crawl_config == {"max_pages": 100}
        assert job.extract_config == {"clean_html": True}
        assert job.vectorize_config == {"chunk_size": 1000}
        assert str(job) == "test-ingest-123 - https://example.com"
    
    def test_crawl_job_status_choices(self, test_organization, test_data_source):
        """Test crawl job status choices."""
        job = CrawlJob.objects.create(
            job_id="test-job-123",
            organization=test_organization,
            data_source=test_data_source,
            root_url="https://example.com"
        )
        
        # Test valid status
        job.status = "running"
        job.save()
        assert job.status == "running"
        
        # Test invalid status (should not raise error, but won't be validated)
        job.status = "invalid_status"
        job.save()
        assert job.status == "invalid_status"
    
    def test_ingest_job_status_choices(self, test_organization):
        """Test ingest job status choices."""
        job = IngestJob.objects.create(
            job_id="test-ingest-123",
            organization=test_organization,
            root_url="https://example.com"
        )
        
        # Test valid status
        job.status = "crawling"
        job.save()
        assert job.status == "crawling"
    
    def test_model_relationships(self, test_organization):
        """Test model relationships."""
        # Create data source
        source = DataSource.objects.create(
            tenant=test_organization,
            name="Test Source",
            source_type="website"
        )
        
        # Create crawl job
        crawl_job = CrawlJob.objects.create(
            job_id="test-crawl-123",
            organization=test_organization,
            data_source=source,
            root_url="https://example.com"
        )
        
        # Create ingest job
        ingest_job = IngestJob.objects.create(
            job_id="test-ingest-123",
            organization=test_organization,
            root_url="https://example.com"
        )
        
        # Test relationships
        assert crawl_job.organization == test_organization
        assert crawl_job.data_source == source
        assert source.tenant == test_organization
        assert ingest_job.organization == test_organization
        
        # Test reverse relationships
        assert crawl_job in test_organization.crawl_jobs.all()
        assert crawl_job in source.crawl_jobs.all()
        assert ingest_job in test_organization.ingest_jobs.all()
        assert source in test_organization.sources.all()


