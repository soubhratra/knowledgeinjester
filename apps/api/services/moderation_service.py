"""
Moderation service for content filtering using OpenAI Moderation API.
"""
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class ModerationService:
    """Service for content moderation using OpenAI Moderation API."""
    
    def __init__(self):
        """Initialize the moderation service with OpenAI client."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def moderate_content(self, content: str) -> Dict[str, Any]:
        """
        Moderate content using OpenAI Moderation API.
        
        Args:
            content: The text content to moderate
            
        Returns:
            Dictionary containing moderation results with keys:
            - flagged: bool - Whether the content was flagged
            - categories: dict - Categories that were flagged
            - category_scores: dict - Confidence scores for each category
            - error: str - Error message if moderation failed
        """
        try:
            response = self.client.moderations.create(input=content)
            
            result = response.results[0]
            
            # Log the flagged status for monitoring
            logger.info(f"Moderation result - flagged: {result.flagged}")
            
            # Log detailed moderation results when content is flagged
            if result.flagged:
                flagged_categories = []
                category_scores = []
                
                # Check each category and log details
                categories = {
                    "hate": result.categories.hate,
                    "hate_threatening": result.categories.hate_threatening,
                    "self_harm": result.categories.self_harm,
                    "sexual": result.categories.sexual,
                    "sexual_minors": result.categories.sexual_minors,
                    "violence": result.categories.violence,
                    "violence_graphic": result.categories.violence_graphic,
                }
                
                scores = {
                    "hate": result.category_scores.hate,
                    "hate_threatening": result.category_scores.hate_threatening,
                    "self_harm": result.category_scores.self_harm,
                    "sexual": result.category_scores.sexual,
                    "sexual_minors": result.category_scores.sexual_minors,
                    "violence": result.category_scores.violence,
                    "violence_graphic": result.category_scores.violence_graphic,
                }
                
                for category, is_flagged in categories.items():
                    if is_flagged:
                        flagged_categories.append(category)
                        category_scores.append(f"{category}: {scores[category]:.3f}")
                
                logger.warning(f"Content flagged - Categories: {', '.join(flagged_categories)}")
                logger.warning(f"Content flagged - Scores: {', '.join(category_scores)}")
            
            return {
                "flagged": result.flagged,
                "categories": {
                    "hate": result.categories.hate,
                    "hate_threatening": result.categories.hate_threatening,
                    "self_harm": result.categories.self_harm,
                    "sexual": result.categories.sexual,
                    "sexual_minors": result.categories.sexual_minors,
                    "violence": result.categories.violence,
                    "violence_graphic": result.categories.violence_graphic,
                },
                "category_scores": {
                    "hate": result.category_scores.hate,
                    "hate_threatening": result.category_scores.hate_threatening,
                    "self_harm": result.category_scores.self_harm,
                    "sexual": result.category_scores.sexual,
                    "sexual_minors": result.category_scores.sexual_minors,
                    "violence": result.category_scores.violence,
                    "violence_graphic": result.category_scores.violence_graphic,
                },
                "error": None
            }
            
        except Exception as e:
            # Log moderation failure
            logger.warning(f"Moderation API failed - flagged: False (fallback), error: {str(e)}")
            return {
                "flagged": False,  # Default to not flagged if moderation fails
                "categories": {},
                "category_scores": {},
                "error": f"Moderation API error: {str(e)}"
            }
    
    def is_content_appropriate(self, content: str, threshold: float = 0.5) -> bool:
        """
        Check if content is appropriate based on moderation results.
        
        Args:
            content: The text content to check
            threshold: Confidence threshold for flagging (0.0 to 1.0)
            
        Returns:
            True if content is appropriate, False otherwise
        """
        moderation_result = self.moderate_content(content)
        
        if moderation_result["error"]:
            # If moderation fails, allow content through but log the error
            print(f"WARNING: Moderation failed for content: {moderation_result['error']}")
            return True
        
        if not moderation_result["flagged"]:
            return True
        
        # Check if any category score exceeds the threshold
        for category, score in moderation_result["category_scores"].items():
            if score > threshold:
                return False
        
        return True
    
    def get_moderation_reason(self, content: str, threshold: float = 0.5) -> Optional[str]:
        """
        Get the reason why content was flagged as inappropriate.
        
        Args:
            content: The text content to check
            threshold: Confidence threshold for flagging (0.0 to 1.0)
            
        Returns:
            String describing why content was flagged, or None if appropriate
        """
        moderation_result = self.moderate_content(content)
        
        if moderation_result["error"]:
            return f"Moderation error: {moderation_result['error']}"
        
        if not moderation_result["flagged"]:
            return None
        
        flagged_categories = []
        for category, score in moderation_result["category_scores"].items():
            if score > threshold:
                flagged_categories.append(f"{category} (confidence: {score:.2f})")
        
        if flagged_categories:
            return f"Content flagged for: {', '.join(flagged_categories)}"
        
        return "Content flagged by moderation API"
    
    def moderate_question(self, question: str) -> Dict[str, Any]:
        """
        Moderate a user question specifically.
        
        Args:
            question: The user's question to moderate
            
        Returns:
            Dictionary with moderation results and appropriate response
        """
        moderation_result = self.moderate_content(question)
        
        if moderation_result["error"]:
            return {
                "is_appropriate": True,  # Allow through if moderation fails
                "reason": None,
                "moderation_result": moderation_result,
                "response": None
            }
        
        if not moderation_result["flagged"]:
            return {
                "is_appropriate": True,
                "reason": None,
                "moderation_result": moderation_result,
                "response": None
            }
        
        # Content is flagged as inappropriate
        reason = self.get_moderation_reason(question)
        response = "I'm sorry, but I cannot answer this question as it contains inappropriate content. Please ask a respectful and constructive question that I can help you with."
        
        return {
            "is_appropriate": False,
            "reason": reason,
            "moderation_result": moderation_result,
            "response": response
        }
