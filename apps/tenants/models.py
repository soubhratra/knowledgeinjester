"""
Multi-tenant models for data isolation.
"""
from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    """Organization/tenant model."""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    tenant_id = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Supabase configuration per tenant
    supabase_url = models.URLField(blank=True)
    supabase_anon_key = models.CharField(max_length=500, blank=True)
    supabase_service_key = models.CharField(max_length=500, blank=True)
    
    # Custom prompt configuration per tenant
    custom_prompt = models.TextField(
        blank=True,
        help_text="Custom prompt template for this organization. Use {context}, {question}, and {sources} as placeholders. If empty, default prompt will be used."
    )
    
    class Meta:
        db_table = 'organizations'
    
    def __str__(self):
        return self.name


class DataSource(models.Model):
    """Data source configuration per organization."""
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sources")
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=[
        ('website', 'Website'),
        ('document', 'Document Upload'),
        ('api', 'API'),
    ])
    config = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'data_sources'
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class CrawlJob(models.Model):
    """Crawl job tracking."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    job_id = models.CharField(max_length=100, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='crawl_jobs')
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='crawl_jobs')
    root_url = models.URLField()
    max_pages = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    config = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'crawl_jobs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_id} - {self.root_url}"


class IngestJob(models.Model):
    """End-to-end ingestion job tracking."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('crawling', 'Crawling'),
        ('extracting', 'Extracting'),
        ('vectorizing', 'Vectorizing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    job_id = models.CharField(max_length=100, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ingest_jobs')
    root_url = models.URLField()
    max_pages = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    crawl_config = models.JSONField(default=dict)
    extract_config = models.JSONField(default=dict)
    vectorize_config = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ingest_jobs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_id} - {self.root_url}"


class ActivityAudit(models.Model):
    """Audit trail for tenant activities like ingest and cleanup operations."""
    
    ACTIVITY_TYPES = [
        ('ingest', 'Ingest'),
        ('cleanup', 'Cleanup'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=64, db_index=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    performed_by = models.CharField(max_length=100, default='admin')
    details = models.JSONField(default=dict, help_text="Additional details about the activity")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activity_audit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant_id} - {self.activity_type} by {self.performed_by} at {self.created_at}"


