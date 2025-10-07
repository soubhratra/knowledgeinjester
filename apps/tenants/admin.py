"""
Admin configuration for tenant models.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Organization, DataSource, CrawlJob, IngestJob, ActivityAudit, Conversation, Session


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'site_key', 'tenant_id', 'status', 'env', 'created_at']
    list_filter = ['status', 'env', 'created_at']
    search_fields = ['name', 'slug', 'tenant_id', 'site_key', 'domain']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'tenant_id')
        }),
        ('Security Configuration', {
            'fields': ('site_key', 'allowed_origins', 'domain', 'status', 'env'),
            'description': 'Configure site-key based security and allowed origins for CORS'
        }),
        ('Supabase Configuration', {
            'fields': ('supabase_url', 'supabase_anon_key', 'supabase_service_key'),
            'classes': ('collapse',)
        }),
        ('Custom Prompt', {
            'fields': ('custom_prompt',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DataSource)
class DataSourceAdmin(ModelAdmin):
    list_display = ['name', 'tenant', 'source_type', 'active', 'created_at']
    list_filter = ['source_type', 'active', 'created_at']
    search_fields = ['name', 'tenant__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CrawlJob)
class CrawlJobAdmin(ModelAdmin):
    list_display = ['job_id', 'organization', 'root_url', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job_id', 'root_url', 'organization__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(IngestJob)
class IngestJobAdmin(ModelAdmin):
    list_display = ['job_id', 'organization', 'root_url', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job_id', 'root_url', 'organization__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ['conversation_id', 'site_key', 'tenant_id', 'origin', 'message_count', 'created_at', 'last_seen_at']
    list_filter = ['created_at', 'last_seen_at']
    search_fields = ['conversation_id', 'site_key', 'tenant_id', 'origin', 'ip_address']
    readonly_fields = ['created_at', 'last_seen_at']
    ordering = ['-last_seen_at']
    
    fieldsets = (
        ('Conversation Information', {
            'fields': ('conversation_id', 'organization', 'tenant_id', 'site_key')
        }),
        ('Security', {
            'fields': ('origin', 'ip_address')
        }),
        ('Metadata', {
            'fields': ('message_count', 'page_url_hash', 'nonce', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_seen_at')
        }),
    )


@admin.register(Session)
class SessionAdmin(ModelAdmin):
    list_display = ['session_id', 'site_key', 'origin', 'issued_at', 'expires_at', 'revoked', 'request_count']
    list_filter = ['revoked', 'issued_at', 'expires_at']
    search_fields = ['session_id', 'site_key', 'tenant_id', 'origin', 'ip_address']
    readonly_fields = ['issued_at', 'last_used_at', 'revoked_at']
    ordering = ['-issued_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'organization', 'tenant_id', 'site_key')
        }),
        ('Security', {
            'fields': ('origin', 'ip_address', 'revoked', 'revoked_at')
        }),
        ('Token Metadata', {
            'fields': ('issued_at', 'expires_at', 'last_used_at', 'request_count')
        }),
    )
    
    actions = ['revoke_sessions']
    
    def revoke_sessions(self, request, queryset):
        """Bulk revoke sessions"""
        from django.utils import timezone
        count = queryset.update(revoked=True, revoked_at=timezone.now())
        self.message_user(request, f'Successfully revoked {count} session(s).')
    revoke_sessions.short_description = "Revoke selected sessions"


@admin.register(ActivityAudit)
class ActivityAuditAdmin(ModelAdmin):
    list_display = ['tenant_id', 'site_key', 'activity_type', 'performed_by', 'origin', 'ip_address', 'created_at']
    list_filter = ['activity_type', 'performed_by', 'created_at']
    search_fields = ['tenant_id', 'site_key', 'performed_by', 'origin', 'ip_address']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('tenant_id', 'site_key', 'activity_type', 'performed_by')
        }),
        ('Security', {
            'fields': ('origin', 'ip_address')
        }),
        ('Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
