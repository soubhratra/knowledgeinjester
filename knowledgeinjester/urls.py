from django.urls import path
from apps.api.router import api

urlpatterns = [
    path("api/", api.urls),
]
