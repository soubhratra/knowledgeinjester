"""
Tests for the prompt service functionality.
"""
import pytest
from django.test import TestCase
from apps.tenants.models import Organization
from apps.api.services.prompt_service import PromptService


class TestPromptService(TestCase):
    """Test cases for PromptService."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            tenant_id="test-tenant-123"
        )
        
        self.custom_prompt_template = """You are a specialized assistant for {organization_name}.

Context:
{context}

Question: {question}

Please provide a detailed answer based on the context above. Include specific examples and cite sources when available.

Sources:
{sources}

If you cannot find the answer in the context, please state that clearly."""

    def test_get_prompt_with_custom_template(self):
        """Test getting prompt with custom template."""
        # Set custom prompt for organization
        self.organization.custom_prompt = self.custom_prompt_template
        self.organization.save()
        
        context = "Test context about AI and machine learning."
        question = "What is machine learning?"
        sources = "[1] AI Basics - https://example.com/ai-basics"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that the custom template was used
        self.assertIn("specialized assistant", prompt)
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn(sources, prompt)
        self.assertNotIn("You are a helpful assistant", prompt)  # Default prompt text
        
        # Check that safety instructions are appended
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("inappropriate content", prompt)

    def test_get_prompt_with_default_fallback(self):
        """Test getting prompt with default fallback when no custom prompt."""
        context = "Test context about AI and machine learning."
        question = "What is machine learning?"
        sources = "[1] AI Basics - https://example.com/ai-basics"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that the default prompt was used
        self.assertIn("You are a helpful assistant", prompt)
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn(sources, prompt)
        self.assertIn("Cite sources by number", prompt)
        
        # Check that safety instructions are appended
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("inappropriate content", prompt)

    def test_get_prompt_without_citations(self):
        """Test getting prompt without citations."""
        context = "Test context about AI and machine learning."
        question = "What is machine learning?"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=False,
            context=context,
            question=question,
            sources=""
        )
        
        # Check that the no-citations default prompt was used
        self.assertIn("You are a helpful assistant", prompt)
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn("Do not include any citations", prompt)
        
        # Check that safety instructions are appended
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("inappropriate content", prompt)

    def test_get_prompt_nonexistent_organization(self):
        """Test getting prompt for non-existent organization falls back to default."""
        context = "Test context."
        question = "Test question?"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="nonexistent-tenant",
            enable_citations=True,
            context=context,
            question=question,
            sources=""
        )
        
        # Should fall back to default
        self.assertIn("You are a helpful assistant", prompt)
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        
        # Check that safety instructions are appended
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("inappropriate content", prompt)

    def test_get_prompt_template_for_organization(self):
        """Test getting raw prompt template for organization."""
        # Test with custom prompt
        self.organization.custom_prompt = self.custom_prompt_template
        self.organization.save()
        
        template = PromptService.get_prompt_template_for_organization("test-tenant-123")
        self.assertEqual(template, self.custom_prompt_template)
        
        # Test with empty prompt (should return None)
        self.organization.custom_prompt = ""
        self.organization.save()
        
        template = PromptService.get_prompt_template_for_organization("test-tenant-123")
        self.assertIsNone(template)

    def test_validate_prompt_template(self):
        """Test prompt template validation."""
        # Valid template
        valid_template = "Context: {context}\nQuestion: {question}\nAnswer:"
        self.assertTrue(PromptService.validate_prompt_template(valid_template))
        
        # Invalid template (missing required placeholders)
        invalid_template = "Context: {context}\nAnswer:"
        self.assertFalse(PromptService.validate_prompt_template(invalid_template))
        
        # Invalid template (missing context)
        invalid_template2 = "Question: {question}\nAnswer:"
        self.assertFalse(PromptService.validate_prompt_template(invalid_template2))

    def test_custom_prompt_with_organization_name_placeholder(self):
        """Test custom prompt that includes organization name placeholder."""
        custom_prompt = """You are an AI assistant for {organization_name}.

Context:
{context}

Question: {question}

Please provide a helpful answer based on the context.

Sources:
{sources}"""
        
        self.organization.custom_prompt = custom_prompt
        self.organization.save()
        
        context = "Test context"
        question = "Test question"
        sources = "Test sources"
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # The organization name placeholder should be replaced with the actual organization name
        self.assertIn("Test Organization", prompt)  # Organization name should be replaced
        self.assertNotIn("{organization_name}", prompt)  # Placeholder should be replaced
        self.assertIn(context, prompt)
        self.assertIn(question, prompt)
        self.assertIn(sources, prompt)
        
        # Check that safety instructions are appended
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("inappropriate content", prompt)
    
    def test_safety_instructions_always_appended(self):
        """Test that safety instructions are always appended to all prompts."""
        context = "Test context"
        question = "Test question"
        sources = "Test sources"
        
        # Test with custom prompt
        custom_prompt = "Custom prompt for {organization_name}.\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nSources:\n{sources}"
        self.organization.custom_prompt = custom_prompt
        self.organization.save()
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that safety instructions are present
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("vulgarity, profanity, or abusive language", prompt)
        self.assertIn("inappropriate content", prompt)
        
        # Test with default prompt (no custom prompt)
        self.organization.custom_prompt = ""
        self.organization.save()
        
        prompt = PromptService.get_prompt_for_organization(
            tenant_id="test-tenant-123",
            enable_citations=True,
            context=context,
            question=question,
            sources=sources
        )
        
        # Check that safety instructions are present
        self.assertIn("SAFETY GUIDELINES", prompt)
        self.assertIn("legally and ethically valid", prompt)
        self.assertIn("vulgarity, profanity, or abusive language", prompt)
        self.assertIn("inappropriate content", prompt)
