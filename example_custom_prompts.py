#!/usr/bin/env python3
"""
Example script demonstrating how to use custom prompts for different organizations.

This script shows how to:
1. Create organizations with custom prompts
2. Use the prompt service to get organization-specific prompts
3. Demonstrate fallback to default prompts
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knowledgeinjester.settings')
django.setup()

from apps.tenants.models import Organization
from apps.api.services.prompt_service import PromptService


def create_example_organizations():
    """Create example organizations with different custom prompts."""
    
    # Organization 1: Medical AI Assistant
    medical_org, created = Organization.objects.get_or_create(
        tenant_id="medical-ai-123",
        defaults={
            'name': 'Medical AI Solutions',
            'slug': 'medical-ai-solutions',
            'custom_prompt': """You are a specialized medical AI assistant for {organization_name}.

Context:
{context}

Question: {question}

Instructions:
- Provide accurate, evidence-based medical information
- Always recommend consulting with healthcare professionals for medical decisions
- Cite sources using [1], [2], etc. when referencing medical literature
- Be cautious with medical advice and emphasize the importance of professional consultation
- If information is not available in the context, clearly state this limitation

Sources:
{sources}

Remember: This information is for educational purposes only and should not replace professional medical advice.""",
        }
    )
    
    # Organization 2: Legal Research Assistant
    legal_org, created = Organization.objects.get_or_create(
        tenant_id="legal-research-456",
        defaults={
            'name': 'Legal Research Corp',
            'slug': 'legal-research-corp',
            'custom_prompt': """You are a legal research assistant for {organization_name}.

Context:
{context}

Question: {question}

Instructions:
- Provide precise legal information based on the provided context
- Cite legal sources using [1], [2], etc. with proper legal citation format
- Distinguish between different jurisdictions and legal systems when relevant
- Always note that this is not legal advice and recommend consulting with qualified attorneys
- Be specific about case law, statutes, and regulations when available

Sources:
{sources}

Disclaimer: This information is for research purposes only and does not constitute legal advice.""",
        }
    )
    
    # Organization 3: Default prompt (no custom prompt)
    default_org, created = Organization.objects.get_or_create(
        tenant_id="default-org-789",
        defaults={
            'name': 'Default Organization',
            'slug': 'default-org',
            'custom_prompt': '',  # Empty custom prompt to use defaults
        }
    )
    
    return medical_org, legal_org, default_org


def demonstrate_prompt_usage():
    """Demonstrate how different organizations get different prompts."""
    
    print("=== Custom Prompt Demonstration ===\n")
    
    # Create example organizations
    medical_org, legal_org, default_org = create_example_organizations()
    
    # Sample context and question
    context = "The patient presents with symptoms of chest pain and shortness of breath. Medical records show a history of hypertension and diabetes."
    question = "What are the potential causes of chest pain in this patient?"
    sources = "[1] Cardiology Guidelines - https://example.com/cardio\n[2] Emergency Medicine Protocols - https://example.com/emergency"
    
    # Test Medical AI Organization
    print("1. Medical AI Organization:")
    print(f"   Organization: {medical_org.name}")
    print(f"   Tenant ID: {medical_org.tenant_id}")
    medical_prompt = PromptService.get_prompt_for_organization(
        tenant_id=medical_org.tenant_id,
        enable_citations=True,
        context=context,
        question=question,
        sources=sources
    )
    print(f"   Prompt preview: {medical_prompt[:200]}...")
    print(f"   Contains medical disclaimer: {'medical advice' in medical_prompt}")
    print(f"   Contains organization name: {'Medical AI Solutions' in medical_prompt}")
    print()
    
    # Test Legal Research Organization
    print("2. Legal Research Organization:")
    print(f"   Organization: {legal_org.name}")
    print(f"   Tenant ID: {legal_org.tenant_id}")
    legal_prompt = PromptService.get_prompt_for_organization(
        tenant_id=legal_org.tenant_id,
        enable_citations=True,
        context=context,
        question=question,
        sources=sources
    )
    print(f"   Prompt preview: {legal_prompt[:200]}...")
    print(f"   Contains legal disclaimer: {'legal advice' in legal_prompt}")
    print(f"   Contains organization name: {'Legal Research Corp' in legal_prompt}")
    print()
    
    # Test Default Organization
    print("3. Default Organization (no custom prompt):")
    print(f"   Organization: {default_org.name}")
    print(f"   Tenant ID: {default_org.tenant_id}")
    default_prompt = PromptService.get_prompt_for_organization(
        tenant_id=default_org.tenant_id,
        enable_citations=True,
        context=context,
        question=question,
        sources=sources
    )
    print(f"   Prompt preview: {default_prompt[:200]}...")
    print(f"   Uses default prompt: {'You are a helpful assistant' in default_prompt}")
    print()
    
    # Test non-existent organization
    print("4. Non-existent Organization (fallback to default):")
    nonexistent_prompt = PromptService.get_prompt_for_organization(
        tenant_id="nonexistent-org",
        enable_citations=True,
        context=context,
        question=question,
        sources=sources
    )
    print(f"   Prompt preview: {nonexistent_prompt[:200]}...")
    print(f"   Uses default prompt: {'You are a helpful assistant' in nonexistent_prompt}")
    print()
    
    # Test prompt template retrieval
    print("5. Prompt Template Retrieval:")
    medical_template = PromptService.get_prompt_template_for_organization(medical_org.tenant_id)
    default_template = PromptService.get_prompt_template_for_organization(default_org.tenant_id)
    
    print(f"   Medical org has custom template: {medical_template is not None}")
    print(f"   Default org has custom template: {default_template is not None}")
    print()
    
    # Test prompt validation
    print("6. Prompt Template Validation:")
    valid_template = "Context: {context}\nQuestion: {question}\nAnswer:"
    invalid_template = "Context: {context}\nAnswer:"  # Missing {question}
    
    print(f"   Valid template validation: {PromptService.validate_prompt_template(valid_template)}")
    print(f"   Invalid template validation: {PromptService.validate_prompt_template(invalid_template)}")


if __name__ == "__main__":
    demonstrate_prompt_usage()
