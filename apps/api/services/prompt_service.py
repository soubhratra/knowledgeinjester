"""
Prompt service for handling organization-specific prompts with fallback to defaults.
"""
from typing import Optional
from apps.tenants.models import Organization


class PromptService:
    """Service for managing organization-specific prompts."""
    
    # Safety instructions that will be appended to all prompts
    SAFETY_INSTRUCTIONS = """

SAFETY GUIDELINES:
Before answering, please ensure the question is appropriate and follows these guidelines:
- The question should be legally and ethically valid
- No vulgarity, profanity, or abusive language should be present
- The question should be respectful and constructive
- If the question violates these guidelines, politely decline to answer and explain why

If the question is inappropriate, respond with: "I'm sorry, but I cannot answer this question as it contains inappropriate content. Please ask a respectful and constructive question that I can help you with."
"""
    
    # Default prompts as class constants
    DEFAULT_PROMPT_WITH_CITATIONS = """You are a helpful assistant. Use the context to answer accurately.

Context:
{context}

Question: {question}

Instructions:
- Cite sources by number like [1], [2] when helpful
- Use citation numbers in chronological order - [1] should come before [2], [2] before [3], etc.
- Keep citations relevant and concise (3-5 sources max)
- Do not fabricate sources - only cite from the provided context
- If unsure about a citation, omit it rather than guessing
- For follow-up questions, reuse the same numbering if you reference the same sources

Sources:
{sources}

If the context is insufficient, say so briefly and answer to the best of your ability.
"""

    DEFAULT_PROMPT_WITHOUT_CITATIONS = """You are a helpful assistant. Use the context to answer accurately.

Context:
{context}

Question: {question}

Answer the question based on the provided context. Do not include any citations or source references in your response.

If the context is insufficient, say so briefly and answer to the best of your ability.
"""

    @classmethod
    def get_prompt_for_organization(
        cls, 
        tenant_id: str, 
        enable_citations: bool = True,
        context: str = "",
        question: str = "",
        sources: str = ""
    ) -> str:
        """
        Get the appropriate prompt for an organization.
        
        Args:
            tenant_id: The tenant/organization ID
            enable_citations: Whether to include citation instructions
            context: The context to include in the prompt
            question: The question to include in the prompt
            sources: The sources list to include in the prompt
            
        Returns:
            The formatted prompt string
        """
        try:
            organization = Organization.objects.get(tenant_id=tenant_id)
            custom_prompt = organization.custom_prompt
            
            if custom_prompt and custom_prompt.strip():
                # Use custom prompt with placeholders
                # Use safe formatting to handle additional placeholders
                try:
                    formatted_prompt = custom_prompt.format(
                        context=context,
                        question=question,
                        sources=sources,
                        organization_name=organization.name if hasattr(organization, 'name') else tenant_id
                    )
                    # Append safety instructions to custom prompts
                    return formatted_prompt + cls.SAFETY_INSTRUCTIONS
                except KeyError as e:
                    # If custom prompt has additional placeholders not provided, 
                    # fall back to default prompt
                    pass
        except Organization.DoesNotExist:
            pass
        
        # Fallback to default prompts
        if enable_citations:
            formatted_prompt = cls.DEFAULT_PROMPT_WITH_CITATIONS.format(
                context=context,
                question=question,
                sources=sources
            )
        else:
            formatted_prompt = cls.DEFAULT_PROMPT_WITHOUT_CITATIONS.format(
                context=context,
                question=question,
                sources=sources
            )
        
        # Append safety instructions to default prompts
        return formatted_prompt + cls.SAFETY_INSTRUCTIONS
    
    @classmethod
    def get_prompt_template_for_organization(cls, tenant_id: str) -> Optional[str]:
        """
        Get the raw prompt template for an organization (without formatting).
        
        Args:
            tenant_id: The tenant/organization ID
            
        Returns:
            The raw prompt template or None if using default
        """
        try:
            organization = Organization.objects.get(tenant_id=tenant_id)
            return organization.custom_prompt if organization.custom_prompt and organization.custom_prompt.strip() else None
        except Organization.DoesNotExist:
            return None
    
    @classmethod
    def validate_prompt_template(cls, template: str) -> bool:
        """
        Validate that a prompt template contains the required placeholders.
        
        Args:
            template: The prompt template to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_placeholders = ['{context}', '{question}']
        return all(placeholder in template for placeholder in required_placeholders)
