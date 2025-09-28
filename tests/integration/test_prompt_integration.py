"""
Integration tests for custom prompt functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from apps.tenants.models import Organization
from apps.api.services.prompt_service import PromptService


@pytest.mark.django_db
class TestPromptIntegration:
    """Test custom prompt integration with the system."""
    
    def test_prompt_service_with_medical_organization(self, test_organization_with_custom_prompt):
        """Test prompt service with medical organization."""
        context = "Diabetes is a chronic condition that affects blood sugar levels."
        question = "What are the symptoms of diabetes?"
        sources = "[1] Medical Journal - https://example.com/diabetes"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=test_organization_with_custom_prompt.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that custom prompt was used
        assert "Medical AI Solutions" in prompt  # Organization name should be replaced
        assert "medical AI assistant" in prompt.lower()
        assert "educational purposes only" in prompt.lower()
        assert context in prompt
        assert question in prompt
        assert sources in prompt
        assert "healthcare professionals" in prompt.lower()
    
    def test_prompt_service_with_legal_organization(self, test_organization_with_legal_prompt):
        """Test prompt service with legal organization."""
        context = "A valid contract requires offer, acceptance, and consideration."
        question = "What makes a contract legally binding?"
        sources = "[1] Legal Code - https://example.com/contracts"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=test_organization_with_legal_prompt.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that custom prompt was used
        assert "Legal Research Corp" in prompt  # Organization name should be replaced
        assert "legal research assistant" in prompt.lower()
        assert "not legal advice" in prompt.lower()
        assert context in prompt
        assert question in prompt
        assert sources in prompt
        assert "legal citation format" in prompt.lower()
    
    def test_prompt_service_with_empty_prompt_organization(self, test_organization_with_empty_prompt):
        """Test prompt service with organization that has empty custom prompt."""
        context = "Artificial intelligence is a field of computer science."
        question = "What is artificial intelligence?"
        sources = "[1] AI Textbook - https://example.com/ai"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=test_organization_with_empty_prompt.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that default prompt was used
        assert "You are a helpful assistant" in prompt
        assert "Cite sources by number" in prompt
        assert context in prompt
        assert question in prompt
        assert sources in prompt
        # Should not contain organization-specific language
        assert "Medical AI Solutions" not in prompt
        assert "Legal Research Corp" not in prompt
    
    def test_prompt_service_without_citations(self, test_organization_with_custom_prompt):
        """Test prompt service without citations."""
        context = "Machine learning is a subset of artificial intelligence."
        question = "What is machine learning?"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=test_organization_with_custom_prompt.tenant_id,
            enable_citations=False,
            context=context,
            question=question,
            sources=""
        )
        
        # Should still use custom prompt but without citation instructions
        assert "Medical AI Solutions" in prompt
        assert "medical AI assistant" in prompt.lower()
        assert context in prompt
        assert question in prompt
        # Should not have citation-specific instructions
        assert "Cite sources by number" not in prompt
    
    def test_prompt_service_nonexistent_organization(self):
        """Test prompt service with non-existent organization."""
        context = "Test context"
        question = "Test question?"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="nonexistent-tenant",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Should fall back to default prompt
        assert "You are a helpful assistant" in prompt
        assert context in prompt
        assert question in prompt
        assert sources in prompt
    
    def test_prompt_service_invalid_custom_prompt(self):
        """Test prompt service with invalid custom prompt (missing placeholders)."""
        # Create organization with invalid custom prompt
        org = Organization.objects.create(
            name="Invalid Prompt Org",
            slug="invalid-prompt-org",
            tenant_id="invalid-prompt-123",
            custom_prompt="This is an invalid prompt without required placeholders."
        )
        
        context = "Test context"
        question = "Test question?"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=org.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Should fall back to default prompt due to KeyError
        assert "You are a helpful assistant" in prompt
        assert context in prompt
        assert question in prompt
        assert sources in prompt
        
        # Clean up
        org.delete()
    
    def test_prompt_template_retrieval(self, test_organization_with_custom_prompt, test_organization_with_empty_prompt):
        """Test prompt template retrieval."""
        # Test with custom prompt
        template = PromptService.get_prompt_template_for_organization(
            test_organization_with_custom_prompt.tenant_id
        )
        assert template is not None
        assert "medical AI assistant" in template.lower()
        
        # Test with empty prompt
        template = PromptService.get_prompt_template_for_organization(
            test_organization_with_empty_prompt.tenant_id
        )
        assert template is None
    
    def test_prompt_validation(self):
        """Test prompt template validation."""
        # Valid template
        valid_template = "Context: {context}\nQuestion: {question}\nAnswer:"
        assert PromptService.validate_prompt_template(valid_template) is True
        
        # Invalid template (missing context)
        invalid_template1 = "Question: {question}\nAnswer:"
        assert PromptService.validate_prompt_template(invalid_template1) is False
        
        # Invalid template (missing question)
        invalid_template2 = "Context: {context}\nAnswer:"
        assert PromptService.validate_prompt_template(invalid_template2) is False
        
        # Invalid template (missing both)
        invalid_template3 = "Answer:"
        assert PromptService.validate_prompt_template(invalid_template3) is False
    
    @patch('apps.api.services.prompt_service.Organization.objects.get')
    def test_prompt_service_database_error_handling(self, mock_get):
        """Test prompt service handles database errors gracefully."""
        # Mock database error
        mock_get.side_effect = Exception("Database error")
        
        context = "Test context"
        question = "Test question?"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Should fall back to default prompt
        assert "You are a helpful assistant" in prompt
        assert context in prompt
        assert question in prompt
        assert sources in prompt
    
    def test_prompt_service_with_additional_placeholders(self):
        """Test prompt service with custom prompt containing additional placeholders."""
        # Create organization with custom prompt that has additional placeholders
        custom_prompt = """You are an assistant for {organization_name}.

Context:
{context}

Question: {question}

Additional info: {additional_info}

Sources:
{sources}"""
        
        org = Organization.objects.create(
            name="Additional Placeholder Org",
            slug="additional-placeholder-org",
            tenant_id="additional-placeholder-123",
            custom_prompt=custom_prompt
        )
        
        context = "Test context"
        question = "Test question?"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=org.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Should fall back to default prompt due to missing {additional_info} placeholder
        assert "You are a helpful assistant" in prompt
        assert context in prompt
        assert question in prompt
        assert sources in prompt
        
        # Clean up
        org.delete()
    
    def test_prompt_service_organization_name_replacement(self, test_organization_with_custom_prompt):
        """Test that organization name is properly replaced in custom prompts."""
        context = "Test context"
        question = "Test question?"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=test_organization_with_custom_prompt.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Organization name should be replaced
        assert "Medical AI Solutions" in prompt
        assert "{organization_name}" not in prompt
        
        # Check that the organization name appears in the right context
        assert "assistant for Medical AI Solutions" in prompt or "Medical AI Solutions" in prompt


class TestPromptServiceIntegration(TestCase):
    """Django TestCase for prompt service integration."""
    
    def setUp(self):
        """Set up test data."""
        self.medical_org = Organization.objects.create(
            name="Medical AI Solutions",
            slug="medical-ai-solutions",
            tenant_id="medical-ai-123",
            custom_prompt="""You are a medical AI assistant for {organization_name}.

Context:
{context}

Question: {question}

Sources:
{sources}

This is for educational purposes only."""
        )
        
        self.legal_org = Organization.objects.create(
            name="Legal Research Corp",
            slug="legal-research-corp",
            tenant_id="legal-research-456",
            custom_prompt="""You are a legal research assistant for {organization_name}.

Context:
{context}

Question: {question}

Sources:
{sources}

This is not legal advice."""
        )
    
    def test_prompt_service_integration_medical(self):
        """Test prompt service integration with medical organization."""
        context = "Hypertension is high blood pressure."
        question = "What causes hypertension?"
        sources = "[1] Medical Journal - https://example.com/hypertension"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=self.medical_org.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Verify custom prompt was used
        self.assertIn("Medical AI Solutions", prompt)
        self.assertIn("medical AI assistant", prompt.lower())
        self.assertIn("educational purposes only", prompt.lower())
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn(sources, prompt)
    
    def test_prompt_service_integration_legal(self):
        """Test prompt service integration with legal organization."""
        context = "A contract requires mutual assent."
        question = "What is mutual assent?"
        sources = "[1] Legal Code - https://example.com/contracts"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id=self.legal_org.tenant_id,
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Verify custom prompt was used
        self.assertIn("Legal Research Corp", prompt)
        self.assertIn("legal research assistant", prompt.lower())
        self.assertIn("not legal advice", prompt.lower())
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn(sources, prompt)
    
    def test_prompt_service_fallback_behavior(self):
        """Test prompt service fallback behavior."""
        # Test with non-existent organization
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="nonexistent-tenant",
            enable_citations=True,
            context="Test context",
            question="Test question?",
            sources="Test sources"
        )
        
        # Should use default prompt
        self.assertIn("You are a helpful assistant", prompt)
        self.assertIn("Test context", prompt)
        self.assertIn("Test question?", prompt)
        self.assertIn("Test sources", prompt)
