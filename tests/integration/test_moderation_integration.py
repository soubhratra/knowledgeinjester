"""
Integration tests for moderation functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from apps.api.services.moderation_service import ModerationService


@pytest.mark.django_db
class TestModerationIntegration:
    """Test moderation service integration."""
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_with_real_api_structure(self, mock_openai):
        """Test moderation service with realistic API response structure."""
        # Mock realistic OpenAI moderation response
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        # Set up categories
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.hate_threatening = False
        mock_result.categories.self_harm = False
        mock_result.categories.sexual = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence = True
        mock_result.categories.violence_graphic = False
        
        # Set up category scores
        mock_result.category_scores.hate = 0.85
        mock_result.category_scores.hate_threatening = 0.12
        mock_result.category_scores.self_harm = 0.03
        mock_result.category_scores.sexual = 0.05
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence = 0.72
        mock_result.category_scores.violence_graphic = 0.15
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_content("This is hate speech with violence")
        
        # Verify the response structure
        assert result["flagged"] is True
        assert result["categories"]["hate"] is True
        assert result["categories"]["violence"] is True
        assert result["categories"]["sexual"] is False
        assert result["category_scores"]["hate"] == 0.85
        assert result["category_scores"]["violence"] == 0.72
        assert result["error"] is None
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_clean_content(self, mock_openai):
        """Test moderation service with clean content."""
        # Mock clean content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        mock_result.flagged = False
        mock_result.categories.hate = False
        mock_result.categories.hate_threatening = False
        mock_result.categories.self_harm = False
        mock_result.categories.sexual = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence = False
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.01
        mock_result.category_scores.hate_threatening = 0.02
        mock_result.category_scores.self_harm = 0.01
        mock_result.category_scores.sexual = 0.01
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence = 0.01
        mock_result.category_scores.violence_graphic = 0.01
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_question("What is machine learning?")
        
        assert result["is_appropriate"] is True
        assert result["reason"] is None
        assert result["response"] is None
        assert result["moderation_result"]["flagged"] is False
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_edge_cases(self, mock_openai):
        """Test moderation service with edge cases."""
        service = ModerationService()
        
        # Test with empty string
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        result = service.moderate_content("")
        assert result["flagged"] is False
        
        # Test with very long content
        long_content = "This is a test. " * 1000
        result = service.moderate_content(long_content)
        assert "error" in result or result["flagged"] is not None
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_threshold_behavior(self, mock_openai):
        """Test moderation service threshold behavior."""
        # Mock content with moderate scores
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.hate_threatening = False
        mock_result.categories.self_harm = False
        mock_result.categories.sexual = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence = False
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.3  # Moderate score
        mock_result.category_scores.hate_threatening = 0.1
        mock_result.category_scores.self_harm = 0.05
        mock_result.category_scores.sexual = 0.02
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence = 0.08
        mock_result.category_scores.violence_graphic = 0.03
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        
        # Test with high threshold (should pass)
        result = service.is_content_appropriate("Questionable content", threshold=0.5)
        assert result is True
        
        # Test with low threshold (should fail)
        result = service.is_content_appropriate("Questionable content", threshold=0.2)
        assert result is False


class TestModerationServiceIntegration(TestCase):
    """Django TestCase for moderation service integration."""
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_integration_clean_content(self, mock_openai):
        """Test moderation service integration with clean content."""
        # Mock clean content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        mock_result.flagged = False
        mock_result.categories.hate = False
        mock_result.categories.hate_threatening = False
        mock_result.categories.self_harm = False
        mock_result.categories.sexual = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence = False
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.01
        mock_result.category_scores.hate_threatening = 0.02
        mock_result.category_scores.self_harm = 0.01
        mock_result.category_scores.sexual = 0.01
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence = 0.01
        mock_result.category_scores.violence_graphic = 0.01
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_question("What is artificial intelligence?")
        
        self.assertTrue(result["is_appropriate"])
        self.assertIsNone(result["reason"])
        self.assertIsNone(result["response"])
        self.assertFalse(result["moderation_result"]["flagged"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_integration_inappropriate_content(self, mock_openai):
        """Test moderation service integration with inappropriate content."""
        # Mock inappropriate content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.hate_threatening = False
        mock_result.categories.self_harm = False
        mock_result.categories.sexual = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence = True
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.9
        mock_result.category_scores.hate_threatening = 0.1
        mock_result.category_scores.self_harm = 0.05
        mock_result.category_scores.sexual = 0.02
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence = 0.8
        mock_result.category_scores.violence_graphic = 0.1
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_question("Hate speech with violence")
        
        self.assertFalse(result["is_appropriate"])
        self.assertIn("hate", result["reason"])
        self.assertIn("violence", result["reason"])
        self.assertIn("inappropriate content", result["response"])
        self.assertTrue(result["moderation_result"]["flagged"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_integration_api_error(self, mock_openai):
        """Test moderation service integration with API error."""
        mock_client = MagicMock()
        mock_client.moderations.create.side_effect = Exception("OpenAI API Error")
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_question("Test question")
        
        # Should allow through if moderation fails
        self.assertTrue(result["is_appropriate"])
        self.assertIsNone(result["reason"])
        self.assertIsNone(result["response"])
        self.assertIn("OpenAI API Error", result["moderation_result"]["error"])
    
    def test_moderation_service_initialization(self):
        """Test moderation service initialization."""
        service = ModerationService()
        self.assertIsNotNone(service.client)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderation_service_all_categories(self, mock_openai):
        """Test moderation service with all categories flagged."""
        # Mock response with all categories flagged
        mock_response = MagicMock()
        mock_result = MagicMock()
        
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.hate_threatening = True
        mock_result.categories.self_harm = True
        mock_result.categories.sexual = True
        mock_result.categories.sexual_minors = True
        mock_result.categories.violence = True
        mock_result.categories.violence_graphic = True
        
        mock_result.category_scores.hate = 0.9
        mock_result.category_scores.hate_threatening = 0.8
        mock_result.category_scores.self_harm = 0.7
        mock_result.category_scores.sexual = 0.6
        mock_result.category_scores.sexual_minors = 0.5
        mock_result.category_scores.violence = 0.4
        mock_result.category_scores.violence_graphic = 0.3
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = ModerationService()
        result = service.moderate_content("Extremely inappropriate content")
        
        self.assertTrue(result["flagged"])
        self.assertTrue(all(result["categories"].values()))
        self.assertTrue(all(score > 0.2 for score in result["category_scores"].values()))
        self.assertIsNone(result["error"])
