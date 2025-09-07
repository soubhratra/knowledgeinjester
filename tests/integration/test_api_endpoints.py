"""
Integration tests for API endpoints.
"""
import json
import pytest
from django.test import Client
from django.urls import reverse

from apps.tenants.models import Organization


@pytest.mark.django_db
class TestAPIEndpoints:
    """Test API endpoint integration."""
    
    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get('/healthz')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'env' in data
    
    def test_crawl_endpoint_success(self, api_client):
        """Test successful crawl endpoint."""
        payload = {
            "url": "https://example.com",
            "max_pages": 3
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        assert 'urls_discovered' in data
        assert 'pages_crawled' in data
        assert 'Vectorized crawl completed' in data['message']
    
    def test_crawl_endpoint_invalid_url(self, api_client):
        """Test crawl endpoint with invalid URL."""
        payload = {
            "url": "not-a-valid-url",
            "max_pages": 3
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_crawl_endpoint_missing_url(self, api_client):
        """Test crawl endpoint with missing URL."""
        payload = {
            "max_pages": 3
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 422
    
    def test_crawl_endpoint_invalid_max_pages(self, api_client):
        """Test crawl endpoint with invalid max_pages."""
        payload = {
            "url": "https://example.com",
            "max_pages": -1
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 422
    
    def test_crawl_endpoint_large_max_pages(self, api_client):
        """Test crawl endpoint with too large max_pages."""
        payload = {
            "url": "https://example.com",
            "max_pages": 2000
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 422
    
    def test_crawl_endpoint_default_max_pages(self, api_client):
        """Test crawl endpoint with default max_pages."""
        payload = {
            "url": "https://example.com"
        }
        
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'Vectorized crawl completed' in data['message']
    
    def test_crawl_endpoint_with_tenant(self, api_client, test_organization):
        """Test crawl endpoint with tenant context."""
        payload = {
            "url": "https://example.com",
            "max_pages": 3
        }
        
        # Add tenant header (if implemented)
        response = api_client.post(
            '/v1/crawl',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_TENANT_ID=test_organization.slug
        )
        
        assert response.status_code == 200


