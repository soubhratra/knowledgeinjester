"""
Admin configuration for vectorizer models.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Document, Chunk


@admin.register(Document)
class DocumentAdmin(ModelAdmin):
    list_display = ['id', 'tenant_id', 'title', 'source_url', 'created_at']
    list_filter = ['tenant_id', 'created_at']
    search_fields = ['title', 'source_url', 'tenant_id']
    readonly_fields = ['created_at', 'doc_hash']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant_id', 'title', 'source_url')
        }),
        ('Metadata', {
            'fields': ('doc_hash', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Chunk)
class ChunkAdmin(ModelAdmin):
    list_display = ['id', 'tenant_id', 'document', 'ordinal', 'created_at']
    list_filter = ['tenant_id', 'created_at']
    search_fields = ['text', 'tenant_id', 'document__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant_id', 'document', 'ordinal', 'text')
        }),
        ('Vector Data', {
            'fields': ('embedding', 'ts'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at'),
            'classes': ('collapse',)
        }),
    )
