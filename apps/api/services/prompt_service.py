"""
Prompt service for handling organization-specific prompts with fallback to defaults.
"""
from typing import Optional
from apps.tenants.models import Organization

import re
from datetime import date

class SafeDict(dict):
    def __missing__(self, key):
        # Leave unknown {placeholders} untouched instead of raising KeyError
        return "{" + key + "}"

BASE_INSTRUCTIONS = (
    'You are “AI Assistant”. Act as an AI expert on support for neurodivergent people '
    '(e.g., Autism, ADHD, Jansen-de Vries Syndrome). Be clear, concise, and neurodiversity-affirming. '
    'Do not invent facts.\n\n'
    'PRIORITY OF INFORMATION (strict order)\n'
    '1) Treat the retrieved RAG content in the context above as the single source of truth.\n'
    '2) If a needed detail is not present in the context, do NOT invent site-specific facts '
    '(e.g., schedules, prices, dates, policies, staff names).\n'
    '3) If still helpful, provide widely accepted, high-level general knowledge relevant to the question '
    ' and, if appropriate, ask 1–2 brief clarifying questions.\n'
    '4) If a needed detail is not present in the context, as well as not know by you based on your general knowledge, '
    ' Use simple first person language to answer the question saying you donot know it and try to ask atleast one clarifying question.\n\n'
    'SAFETY & SCOPE\n'
    '- Do not diagnose or provide medical/legal/financial advice. For emergencies, instruct users to contact local emergency services or crisis lines.\n'
    '- Avoid collecting sensitive personal data. If the user shares it, respond without storing or requesting more.\n'
    '- If the user requests actions (apply, contact, calendar), only recommend them if they appear in the provided context.\n\n'
    'STYLE & FORMAT\n'
    '- Start with a one-sentence answer summary.\n'
    '- Follow with 3–6 bullets or short steps. Keep paragraphs short and scannable.\n'
    '- Offer exactly one next step ONLY if the context includes a relevant action/link (e.g., “→ Contact us”).\n'
)

# Conditional add-ons (kept OUTSIDE the DB)
CITATION_RULES = (
    "CITATIONS\n"
    "- Cite sources by number like [1], [2] when helpful\n"
    "- Use citation numbers in chronological order ([1] before [2], etc.)\n"
    "- Keep citations relevant and concise (3–5 sources max)\n"
    "- Do not fabricate sources — only cite from the provided context\n"
    "- If unsure about a citation, omit it rather than guessing\n"
    "- For follow-up questions, reuse the same numbering if you reference the same sources"
)

NO_CITATION_RULES = (
    "CITATIONS\n"
    "- Do not include any citations or source references in your response."
)

INSTRUCTION_CONTAINER = """{instructions}

{citation_rules}

INPUTS
Context:
{context}
{maybe_sources}
Question: {question}
"""

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

    @classmethod
    def get_prompt_for_organization(
        cls,
        tenant_id: str,
        enable_citations: bool = True,
        context: str = "",
        question: str = "",
        sources: str = ""
    ) -> str:
        try:
            org = Organization.objects.get(tenant_id=tenant_id)
            raw_custom = (org.custom_prompt or "").strip()
            # Strip accidental placeholders to avoid duplication
            if "{context}" in raw_custom or "{question}" in raw_custom:
                raw_custom = re.sub(r"\{context\}|\{question\}", "", raw_custom)
            # Fill only benign placeholders (org name, date, etc.)
            instructions = (raw_custom or BASE_INSTRUCTIONS).format_map(SafeDict({
                "organization_name": getattr(org, "name", tenant_id),
                "today": date.today().isoformat(),
            }))
        except Organization.DoesNotExist:
            instructions = BASE_INSTRUCTIONS

        citation_rules = CITATION_RULES if enable_citations else NO_CITATION_RULES

        # Only include a Sources section if citations are enabled and a sources list is provided
        maybe_sources = ""
        if enable_citations and sources.strip():
            # Expect `sources` as a pre-enumerated list, e.g.:
            # [1] Title A — urlA
            # [2] Title B — urlB
            maybe_sources = "\nSources (for your internal reference only):\n{sources}\n".format(sources=sources)

        final_prompt = INSTRUCTION_CONTAINER.format(
            instructions=instructions,
            citation_rules=citation_rules,
            context=context,
            maybe_sources=maybe_sources,
            question=question
        )

        return final_prompt + cls.SAFETY_INSTRUCTIONS