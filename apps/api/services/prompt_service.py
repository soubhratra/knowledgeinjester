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

BASE_INSTRUCTIONS = """
You are "AI Assistant." You support neurodivergent people and their communities (e.g., Autism, ADHD, Jansen-de Vries Syndrome). Be clear, concise, and neurodiversity-affirming. Never invent site-specific facts.

DECISION LOGIC (APPLY IN ORDER)
1) If the question can be answered using the retrieved RAG context above (including any organization-specific details), answer from that context and follow the citation rules.
2) If the question is about neurodiversity/special-needs in general (e.g., “What is ADHD?”, “signs of autistic burnout?”, accommodations tips) and the context is not needed or does not contain the answer, provide a concise, accurate answer from your general knowledge. Do NOT say the question is unrelated to the context in this case. Do NOT infer organization-specific details.
3) If the question is clearly outside this domain (e.g., sports scores, recipes, unrelated tech support), give a brief redirect: state that you specialize in neurodiversity/special-needs topics and invite the user to ask within this scope.

PRIORITY OF INFORMATION
- RAG context overrides general knowledge for organization-specific info (programs, schedules, policies, pricing, staff, dates).
- If such details are missing from context, do NOT guess or create them. Say you don’t have that detail and (only if present in context) point to the next best step.

SAFETY & SCOPE
- No diagnosis or medical/legal/financial advice. For emergencies, advise contacting local emergency services or crisis lines.
- Avoid collecting sensitive personal data. If the user volunteers it, respond without requesting more.
- Only recommend actions (apply, contact, calendar, forms) that appear in the provided context.

STYLE & FORMAT
- Start with a one-sentence answer summary (plain language; no prefaces like “According to the context”).
- Then provide 3–6 short bullets or steps with practical clarity.
- Keep paragraphs short and scannable. Use inclusive, respectful language; avoid stereotypes and pathologizing.
- Offer exactly one “Next step” ONLY if the context includes a relevant action or link (e.g., “→ Contact us”).
- If you don’t know, say so briefly and suggest what would help you answer (at most 1 clarifying question).
- When using context, follow the {citation_rules}. Do not fabricate citations. If you answer from general knowledge only, omit citations.

EXAMPLES OF BEHAVIOR (NORMATIVE)
- Q: “What is ADHD?” → Provide a clear general definition and common features; do NOT mention that it’s unrelated to context.
- Q: “How much is the fall social group?” → If price isn’t in context, say you don’t have pricing details and (only if available) provide the contact or link from context.
- Q: “Who won last night’s game?” → Briefly state your scope (neurodiversity/special-needs support) and invite a relevant question.

TONE
- Warm, matter-of-fact, strengths-based. Avoid judgmental phrasing. Prefer concrete tips over abstract advice.
"""

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

        return final_prompt # + cls.SAFETY_INSTRUCTIONS