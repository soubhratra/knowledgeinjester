from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from apps.api.router import api
from . import admin as project_admin  # Import our admin configuration

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
