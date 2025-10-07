# Custom Prompts for Organizations

This document describes the custom prompt functionality that allows each organization/tenant to have their own specialized prompts for the AI assistant.

## Overview

The system now supports organization-specific prompts that can be customized per tenant. If no custom prompt is set for an organization, the system falls back to the default prompts.

## Features

- **Organization-specific prompts**: Each organization can have its own custom prompt template
- **Fallback to defaults**: If no custom prompt is set, the system uses default prompts
- **Placeholder support**: Custom prompts can use placeholders like `{context}`, `{question}`, `{sources}`, and `{organization_name}`
- **Validation**: Prompt templates can be validated to ensure they contain required placeholders
- **Management commands**: Easy-to-use Django management commands for managing prompts

## Database Changes

A new field `custom_prompt` has been added to the `Organization` model:

```python
custom_prompt = models.TextField(
    blank=True,
    help_text="Custom prompt template for this organization. Use {context}, {question}, and {sources} as placeholders. If empty, default prompt will be used."
)
```

## Usage

### Setting Custom Prompts

#### Using Django Management Command

```bash
# Set prompt from a file
python manage.py set_custom_prompt my-tenant-123 --prompt-file /path/to/prompt.txt --validate

# Set prompt directly
python manage.py set_custom_prompt my-tenant-123 --prompt-text "You are a specialized assistant for {organization_name}..." --validate

# Clear custom prompt (reset to default)
python manage.py set_custom_prompt my-tenant-123 --clear
```

#### Using Django Admin or API

You can also set custom prompts through the Django admin interface or by updating the `custom_prompt` field directly in the database.

### Prompt Template Placeholders

Custom prompts can use the following placeholders:

- `{context}` - The retrieved context from the knowledge base
- `{question}` - The user's question
- `{sources}` - The formatted sources list (only when citations are enabled)
- `{organization_name}` - The name of the organization

### Example Custom Prompts

#### Medical AI Assistant
```
You are a specialized medical AI assistant for {organization_name}.

Context:
{context}

Question: {question}

Instructions:
- Provide accurate, evidence-based medical information
- Always recommend consulting with healthcare professionals for medical decisions
- Cite sources using [1], [2], etc. when referencing medical literature
- Be cautious with medical advice and emphasize the importance of professional consultation

Sources:
{sources}

Remember: This information is for educational purposes only and should not replace professional medical advice.
```

#### Legal Research Assistant
```
You are a legal research assistant for {organization_name}.

Context:
{context}

Question: {question}

Instructions:
- Provide precise legal information based on the provided context
- Cite legal sources using [1], [2], etc. with proper legal citation format
- Distinguish between different jurisdictions and legal systems when relevant
- Always note that this is not legal advice and recommend consulting with qualified attorneys

Sources:
{sources}

Disclaimer: This information is for research purposes only and does not constitute legal advice.
```

## API Integration

The custom prompts are automatically used in the `/ask` endpoint. The system will:

1. Look up the organization by `tenant_id`
2. Check if a custom prompt is set
3. Use the custom prompt with placeholders filled in
4. Fall back to default prompts if no custom prompt is found

## Testing

Run the tests to verify the functionality:

```bash
python manage.py test tests.unit.test_prompt_service
```

## Example Usage

See `example_custom_prompts.py` for a complete example of how to use the custom prompt functionality.

## Migration

After adding the custom prompt field, run the migration:

```bash
python manage.py migrate tenants
```

## Validation

The system includes validation to ensure prompt templates contain the required placeholders (`{context}` and `{question}`). You can validate prompts using:

```python
from apps.api.services.prompt_service import PromptService

is_valid = PromptService.validate_prompt_template(your_prompt_template)
```

## Fallback Behavior

If a custom prompt template has additional placeholders that aren't provided by the system, it will fall back to the default prompts to ensure the system continues to work properly.
