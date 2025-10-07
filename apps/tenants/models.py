"""
Multi-tenant models for data isolation.
"""
from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    """Organization/tenant model with site-key based security."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ]
    
    ENV_CHOICES = [
        ('prod', 'Production'),
        ('stage', 'Staging'),
        ('dev', 'Development'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    # Keep tenant_id as internal identifier, use site_key as public identifier
    tenant_id = models.CharField(max_length=64, unique=True, 
                                help_text="Internal tenant identifier (kept for backward compatibility)")
    site_key = models.CharField(max_length=128, unique=True, db_index=True, null=True, blank=True,
                               help_text="Public site key (e.g., pub_acme_prod_7Hk2x) for client authentication")
    
    # Security fields
    allowed_origins = models.JSONField(default=list,
                                      help_text="List of allowed HTTPS origins (e.g., ['https://www.example.com'])")
    domain = models.CharField(max_length=255, blank=True, 
                             help_text="Primary domain for this organization (for domain validation)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active',
                             help_text="Site status - disabled sites cannot create new conversations")
    env = models.CharField(max_length=20, choices=ENV_CHOICES, default='prod',
                          help_text="Environment (prod, stage, or dev)")
    
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
        indexes = [
            models.Index(fields=['site_key', 'status']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if the given origin is allowed for this organization."""
        if not origin:
            return False
        return origin in self.allowed_origins


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


class Conversation(models.Model):
    """
    Conversation model for tracking conversations with origin-based security.
    Stores conversation metadata including site_key, origin, and tenant_id.
    """
    id = models.BigAutoField(primary_key=True)
    conversation_id = models.CharField(max_length=128, unique=True, db_index=True,
                                      help_text="Public conversation ID (e.g., c_2c1f1d9f...c1b)")
    
    # Tenant relationship
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, 
                                    related_name='conversations', null=True, blank=True)
    tenant_id = models.CharField(max_length=64, db_index=True,
                                help_text="Internal tenant ID copied from Site/Organization")
    site_key = models.CharField(max_length=128, db_index=True,
                               help_text="Public site key for this conversation")
    
    # Security fields
    origin = models.CharField(max_length=512,
                             help_text="Origin header captured from first request (e.g., https://www.customer.org)")
    ip_address = models.GenericIPAddressField(null=True, blank=True,
                                             help_text="IP address of the client that created the conversation")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    message_count = models.PositiveIntegerField(default=0,
                                               help_text="Number of messages in this conversation")
    
    # Optional telemetry
    page_url_hash = models.CharField(max_length=64, blank=True,
                                    help_text="SHA256 hash of the page URL where conversation started")
    nonce = models.CharField(max_length=128, blank=True,
                            help_text="Optional client-provided nonce for tracking")
    metadata = models.JSONField(default=dict,
                               help_text="Additional metadata about the conversation")
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-last_seen_at']
        indexes = [
            models.Index(fields=['site_key', 'created_at']),
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['origin', 'created_at']),
            models.Index(fields=['conversation_id', 'origin']),
        ]
    
    def __str__(self):
        return f"{self.conversation_id} - {self.site_key}"


class Session(models.Model):
    """
    Session model for JWT token tracking (Phase 1).
    Stores session metadata for audit and revocation purposes.
    """
    id = models.BigAutoField(primary_key=True)
    session_id = models.CharField(max_length=128, unique=True, db_index=True,
                                 help_text="Unique session identifier (UUID)")
    
    # Tenant relationship
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, 
                                    related_name='sessions')
    tenant_id = models.CharField(max_length=64, db_index=True)
    site_key = models.CharField(max_length=128, db_index=True)
    
    # Security fields
    origin = models.CharField(max_length=512,
                             help_text="Origin header from session creation request")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Token metadata
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Token expiration time")
    revoked = models.BooleanField(default=False,
                                 help_text="Whether this session has been revoked")
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    last_used_at = models.DateTimeField(auto_now=True)
    request_count = models.PositiveIntegerField(default=0,
                                               help_text="Number of requests made with this session")
    
    class Meta:
        db_table = 'sessions'
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['site_key', 'issued_at']),
            models.Index(fields=['session_id', 'revoked']),
            models.Index(fields=['expires_at', 'revoked']),
        ]
    
    def __str__(self):
        return f"{self.session_id} - {self.site_key}"
    
    def is_valid(self) -> bool:
        """Check if the session is still valid."""
        from django.utils import timezone
        if self.revoked:
            return False
        if self.expires_at < timezone.now():
            return False
        return True


class ActivityAudit(models.Model):
    """Audit trail for tenant activities like ingest and cleanup operations."""
    
    ACTIVITY_TYPES = [
        ('ingest', 'Ingest'),
        ('cleanup', 'Cleanup'),
        ('session_created', 'Session Created'),
        ('conversation_started', 'Conversation Started'),
        ('origin_blocked', 'Origin Blocked'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=64, db_index=True)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    performed_by = models.CharField(max_length=100, default='admin')
    details = models.JSONField(default=dict, help_text="Additional details about the activity")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional security audit fields
    site_key = models.CharField(max_length=128, blank=True, db_index=True)
    origin = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'activity_audit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
            models.Index(fields=['site_key', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant_id} - {self.activity_type} by {self.performed_by} at {self.created_at}"


