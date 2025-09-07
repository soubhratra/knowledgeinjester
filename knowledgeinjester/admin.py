"""
Admin site configuration for Django Unfold.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin

# Configure the admin site
admin.site.site_header = "Knowledge Injester Admin"
admin.site.site_title = "Knowledge Injester"
admin.site.index_title = "Welcome to Knowledge Injester Administration"
