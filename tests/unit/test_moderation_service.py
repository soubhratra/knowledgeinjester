"""
Tests for the moderation service functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from apps.api.services.moderation_service import ModerationService


class TestModerationService(TestCase):
    """Test cases for ModerationService."""
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_content_success(self, mock_openai_class):
        """Test successful content moderation."""
        # Mock OpenAI response
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
        
        mock_result.category_scores.hate = 0.8
        mock_result.category_scores.violence = 0.1
        mock_result.category_scores.sexual = 0.05
        mock_result.category_scores.self_harm = 0.02
        mock_result.category_scores.hate_threatening = 0.03
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence_graphic = 0.04
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_content("This is hate speech")
        
        self.assertTrue(result["flagged"])
        self.assertTrue(result["categories"]["hate"])
        self.assertFalse(result["categories"]["violence"])
        self.assertEqual(result["category_scores"]["hate"], 0.8)
        self.assertIsNone(result["error"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_content_api_error(self, mock_openai_class):
        """Test moderation with API error."""
        mock_client = MagicMock()
        mock_client.moderations.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_content("Test content")
        
        self.assertFalse(result["flagged"])
        self.assertEqual(result["categories"], {})
        self.assertEqual(result["category_scores"], {})
        self.assertIn("API Error", result["error"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_is_content_appropriate_clean_content(self, mock_openai_class):
        """Test appropriate content detection for clean content."""
        # Mock clean content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.is_content_appropriate("What is artificial intelligence?")
        
        self.assertTrue(result)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_is_content_appropriate_inappropriate_content(self, mock_openai_class):
        """Test appropriate content detection for inappropriate content."""
        # Mock inappropriate content response
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
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.is_content_appropriate("Hate speech content", threshold=0.5)
        
        self.assertFalse(result)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_is_content_appropriate_with_threshold(self, mock_openai_class):
        """Test appropriate content detection with custom threshold."""
        # Mock content with moderate scores
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
        
        mock_result.category_scores.hate = 0.3  # Below threshold
        mock_result.category_scores.violence = 0.1
        mock_result.category_scores.sexual = 0.05
        mock_result.category_scores.self_harm = 0.02
        mock_result.category_scores.hate_threatening = 0.03
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence_graphic = 0.04
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        
        # Test with high threshold (should pass)
        result = moderation_service.is_content_appropriate("Questionable content", threshold=0.5)
        self.assertTrue(result)
        
        # Test with low threshold (should fail)
        result = moderation_service.is_content_appropriate("Questionable content", threshold=0.2)
        self.assertFalse(result)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_get_moderation_reason_clean_content(self, mock_openai_class):
        """Test getting moderation reason for clean content."""
        # Mock clean content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        reason = moderation_service.get_moderation_reason("What is machine learning?")
        
        self.assertIsNone(reason)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_get_moderation_reason_flagged_content(self, mock_openai_class):
        """Test getting moderation reason for flagged content."""
        # Mock flagged content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = True
        mock_result.categories.hate = True
        mock_result.categories.violence = True
        mock_result.categories.sexual = False
        mock_result.categories.self_harm = False
        mock_result.categories.hate_threatening = False
        mock_result.categories.sexual_minors = False
        mock_result.categories.violence_graphic = False
        
        mock_result.category_scores.hate = 0.8
        mock_result.category_scores.violence = 0.7
        mock_result.category_scores.sexual = 0.1
        mock_result.category_scores.self_harm = 0.05
        mock_result.category_scores.hate_threatening = 0.03
        mock_result.category_scores.sexual_minors = 0.01
        mock_result.category_scores.violence_graphic = 0.04
        
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        reason = moderation_service.get_moderation_reason("Hate and violence content", threshold=0.5)
        
        self.assertIn("hate", reason)
        self.assertIn("violence", reason)
        self.assertIn("0.80", reason)  # hate score
        self.assertIn("0.70", reason)  # violence score
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_question_appropriate(self, mock_openai_class):
        """Test moderating an appropriate question."""
        # Mock clean content response
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_question("What is artificial intelligence?")
        
        self.assertTrue(result["is_appropriate"])
        self.assertIsNone(result["reason"])
        self.assertIsNone(result["response"])
        self.assertFalse(result["moderation_result"]["flagged"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_question_inappropriate(self, mock_openai_class):
        """Test moderating an inappropriate question."""
        # Mock flagged content response
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
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_question("Hate speech question")
        
        self.assertFalse(result["is_appropriate"])
        self.assertIn("hate", result["reason"])
        self.assertIn("inappropriate content", result["response"])
        self.assertTrue(result["moderation_result"]["flagged"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_question_api_error(self, mock_openai_class):
        """Test moderating question with API error."""
        mock_client = MagicMock()
        mock_client.moderations.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_question("Test question")
        
        # Should allow through if moderation fails
        self.assertTrue(result["is_appropriate"])
        self.assertIsNone(result["reason"])
        self.assertIsNone(result["response"])
        self.assertIn("API Error", result["moderation_result"]["error"])
    
    def test_moderation_service_initialization(self):
        """Test moderation service initialization."""
        # Test that service can be initialized
        service = ModerationService()
        self.assertIsNotNone(service.client)
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_content_empty_string(self, mock_openai_class):
        """Test moderating empty content."""
        # Mock response for empty content
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        result = moderation_service.moderate_content("")
        
        self.assertFalse(result["flagged"])
        self.assertIsNone(result["error"])
    
    @patch('apps.api.services.moderation_service.OpenAI')
    def test_moderate_content_very_long_text(self, mock_openai_class):
        """Test moderating very long text content."""
        # Mock response for long content
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.flagged = False
        mock_response.results = [mock_result]
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create service instance after mocking
        moderation_service = ModerationService()
        long_text = "This is a very long text. " * 1000  # Very long text
        result = moderation_service.moderate_content(long_text)
        
        self.assertFalse(result["flagged"])
        self.assertIsNone(result["error"])