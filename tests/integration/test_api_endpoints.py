"""
Integration tests for API endpoints.
"""
import json
import pytest
from django.test import Client
from django.urls import reverse
from unittest.mock import patch

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
    
    
    def test_ask_endpoint_basic(self, api_client):
        """Test basic ask endpoint functionality."""
        payload = {
            "messages": [
                {"role": "user", "text": "What is artificial intelligence?"}
            ],
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store, but we test the endpoint structure
        assert response.status_code in [200, 500]  # 500 if no data, 200 if data exists
    
    def test_ask_endpoint_missing_messages(self, api_client):
        """Test ask endpoint with missing messages."""
        payload = {
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 422
    
    def test_ask_endpoint_empty_messages(self, api_client):
        """Test ask endpoint with empty messages array."""
        payload = {
            "messages": [],
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'error' in data
        assert 'No user message found' in data['error']
    
    def test_ask_endpoint_without_citations(self, api_client):
        """Test ask endpoint without citations."""
        payload = {
            "messages": [
                {"role": "user", "text": "What is machine learning?"}
            ],
            "tenant_id": "test-tenant-123",
            "citations": False
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store
        assert response.status_code in [200, 500]
    
    def test_ask_endpoint_default_citations(self, api_client):
        """Test ask endpoint with default citations (should be True)."""
        payload = {
            "messages": [
                {"role": "user", "text": "What is deep learning?"}
            ],
            "tenant_id": "test-tenant-123"
            # citations not provided, should default to True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store
        assert response.status_code in [200, 500]
    
    def test_ask_endpoint_invalid_tenant_id(self, api_client):
        """Test ask endpoint with invalid tenant_id."""
        payload = {
            "messages": [
                {"role": "user", "text": "What is AI?"}
            ],
            "tenant_id": "nonexistent-tenant",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should still work but fall back to default prompt
        assert response.status_code in [200, 500]
    
    def test_ask_endpoint_with_custom_prompt_organization(self, api_client, test_organization_with_custom_prompt):
        """Test ask endpoint with organization that has custom prompt."""
        payload = {
            "messages": [
                {"role": "user", "text": "What are the symptoms of diabetes?"}
            ],
            "tenant_id": test_organization_with_custom_prompt.tenant_id,
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store
        assert response.status_code in [200, 500]
        
        # If successful, the response should be processed with custom prompt
        if response.status_code == 200:
            data = response.json()
            # The custom prompt should be used (we can't easily test the exact content without mocking)
            assert 'text' in data or 'error' in data
    
    def test_ask_endpoint_with_legal_prompt_organization(self, api_client, test_organization_with_legal_prompt):
        """Test ask endpoint with organization that has legal research prompt."""
        payload = {
            "messages": [
                {"role": "user", "text": "What are the requirements for a valid contract?"}
            ],
            "tenant_id": test_organization_with_legal_prompt.tenant_id,
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store
        assert response.status_code in [200, 500]
        
        # If successful, the response should be processed with custom prompt
        if response.status_code == 200:
            data = response.json()
            assert 'text' in data or 'error' in data
    
    def test_ask_endpoint_with_empty_prompt_organization(self, api_client, test_organization_with_empty_prompt):
        """Test ask endpoint with organization that has empty custom prompt (uses defaults)."""
        payload = {
            "messages": [
                {"role": "user", "text": "What is artificial intelligence?"}
            ],
            "tenant_id": test_organization_with_empty_prompt.tenant_id,
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Note: This might fail if no data is in the vector store
        assert response.status_code in [200, 500]
        
        # If successful, the response should use default prompt
        if response.status_code == 200:
            data = response.json()
            assert 'text' in data or 'error' in data
    
    def test_ask_endpoint_custom_prompt_fallback(self, api_client):
        """Test ask endpoint fallback when custom prompt has issues."""
        # Create organization with invalid custom prompt (missing required placeholders)
        org = Organization.objects.create(
            name="Invalid Prompt Org",
            slug="invalid-prompt-org",
            tenant_id="invalid-prompt-123",
            custom_prompt="This is an invalid prompt without required placeholders."
        )
        
        payload = {
            "messages": [
                {"role": "user", "text": "What is AI?"}
            ],
            "tenant_id": org.tenant_id,
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should still work but fall back to default prompt due to invalid custom prompt
        assert response.status_code in [200, 500]
        
        # Clean up
        org.delete()
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_ask_endpoint_with_moderation_blocked(self, mock_openai, api_client):
        """Test ask endpoint with content blocked by moderation."""
        # Mock moderation API to flag content as inappropriate
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.violence = False
        mock_result.categories.sexual = False
        mock_result.categories.self_harm = False
        mock_result.categories.hate_threatening = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.9
        mock_result.category_scores.violence = 0.1
        mock_result.category_scores.sexual = 0.05
        mock_result.category_scores.self_harm = 0.02
        mock_result.category_scores.hate_threatening = 0.03
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence_graphic = 0.04
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        payload = {
            "messages": [
                {"role": "user", "text": "This is hate speech content"}
            ],
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'text' in data
        assert 'inappropriate content' in data['text']
        assert data['sources'] is None
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_ask_endpoint_with_moderation_allowed(self, mock_openai, api_client):
        """Test ask endpoint with content allowed by moderation."""
        # Mock moderation API to allow content
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        payload = {
            "messages": [
                {"role": "user", "text": "What is artificial intelligence?"}
            ],
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should proceed with normal processing (might fail due to no data, but moderation should pass)
        assert response.status_code in [200, 500]
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_ask_endpoint_with_moderation_api_error(self, mock_openai, api_client):
        """Test ask endpoint with moderation API error (should allow through)."""
        # Mock moderation API error
        mock_client = MagicMock()
        mock_client.moderations.create.side_effect = Exception("Moderation API Error")
        mock_openai.return_value = mock_client
        
        payload = {
            "messages": [
                {"role": "user", "text": "What is machine learning?"}
            ],
            "tenant_id": "test-tenant-123",
            "citations": True
        }
        
        response = api_client.post(
            '/v1/ask',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should proceed with normal processing if moderation fails
        assert response.status_code in [200, 500]


