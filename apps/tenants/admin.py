"""
Admin configuration for tenant models.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Organization, DataSource, CrawlJob, IngestJob


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'tenant_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug', 'tenant_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'tenant_id')
        }),
        ('Supabase Configuration', {
            'fields': ('supabase_url', 'supabase_anon_key', 'supabase_service_key'),
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
