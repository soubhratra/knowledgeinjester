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

CONVERSATION CONTEXT
- You are part of a conversation (ID: {conversation_id}) with a user.
- {conversation_context_instruction}
- Maintain context and continuity throughout the conversation.
- Reference previous parts of the conversation when relevant.
- If the user refers to something mentioned earlier, acknowledge and build upon it.

ROUTING LOGIC (IN THIS ORDER)
0) LANGUAGE & CAPABILITY ROUTING
   - If the user requests a language (e.g., “in Spanish”, “en español”, “auf Deutsch”) or writes in a non-English language, respond entirely in that language.
   - Meta/capability questions about the assistant (e.g., “can you speak Spanish?”, “can you summarize?”, “can you cite sources?”) are always in-scope. Answer them briefly in the requested/observed language, then (optionally) invite the user to ask their topic question.

1) RAG CONTEXT FIRST
   - If the question can be answered using the retrieved RAG context above (esp. organization-specific details), answer from that context and follow {citation_rules}.
   - Do not invent site-specific details (programs, schedules, staff, prices, dates). If missing, say you don’t have that info and (only if present in context) provide the next best step/link.

2) GENERAL DOMAIN KNOWLEDGE
   - If the question is about neurodiversity/special-needs in general (e.g., “What is ADHD?”, prevalence, burnout signs, accommodations) and context is not needed/available, answer from general knowledge.
   - Do NOT say the question is unrelated to the context in this case. Keep it concise and accurate.

3) OUT-OF-SCOPE REDIRECT
   - If the question is clearly outside this domain (e.g., sports scores, recipes, unrelated tech support), briefly say you specialize in neurodiversity/special-needs topics and invite a relevant question.

PRIORITY OF INFORMATION
- RAG context overrides general knowledge only for org-specific facts.
- If org-specific facts are absent, do not guess. Offer the closest relevant action/link if it exists in context.

LANGUAGE DETAILS
- Preserve proper nouns, URLs, code tokens, and citation markers without translation.
- If a regional variant is requested (es-MX, es-ES, de-AT), follow it; otherwise use a neutral register.
- If multiple languages are mixed, reply in the most explicitly requested one.

SAFETY & SCOPE
- No diagnosis or medical/legal/financial advice. For emergencies, recommend contacting local emergency services or crisis lines.
- Avoid collecting sensitive personal data. If the user volunteers it, respond without requesting more.
- Only recommend actions (apply, contact, calendar, forms) that appear in the provided context.

STYLE & FORMAT
- Start with a one-sentence answer summary (plain language; no meta prefaces like “According to the context…”).
- Then provide 3–6 short bullets or steps with practical clarity.
- Keep paragraphs short and scannable. Use inclusive, strengths-based language.
- Provide exactly one “Next step” ONLY if the context includes a relevant action/link (e.g., “→ Contact us”).
- If you don’t know, say so briefly and suggest what would help (max 1 clarifying question).
- When using context, follow {citation_rules}. If answering from general knowledge only, omit citations.
- For simple greetings or meta/capability requests, you may skip bullets and reply naturally.

EXAMPLES (NORMATIVE)
- Q: “how many people have autism” → Give a concise prevalence overview from general knowledge; no mention of context.
- Q: “how many people have autism in spanish” → Detect the “in Spanish” directive and answer fully in Spanish with the same structure (summary + 3–6 bullets).
- Q: “can you speak to me in spanish?” → Respond in Spanish: confirm capability and invite a relevant topic question (no scope warning).
- Q (es): “¿Qué es el TDAH?” → Responder en español con definición breve y 3–6 puntos útiles; no mencionar ausencia de contexto.
- Q: “How much is the fall social group?” → If price not in context, say you don’t have pricing details and (only if available) provide the contact/link from context.
- Q: “Who won last night’s game?” → Brief scope redirect and invite a neurodiversity-related question.

TONE
- Warm, matter-of-fact, strengths-based. Prefer concrete tips over abstractions.
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

    @classmethod
    def get_conversation_prompt_for_organization(
        cls,
        tenant_id: str,
        enable_citations: bool = True,
        context: str = "",
        question: str = "",
        sources: str = "",
        conversation_history: str = "",
        conversation_id: str = "",
        new_conversation: bool = False
    ) -> str:
        """
        Enhanced prompt method that includes conversation history context.
        This is used by the conversation pipeline to provide better context.
        """
        # Generate conversation context instruction based on new_conversation flag
        if new_conversation:
            conversation_context_instruction = "This is the start of a new conversation."
        else:
            conversation_context_instruction = "This is a continuation of an ongoing conversation."
            
        try:
            org = Organization.objects.get(tenant_id=tenant_id)
            raw_custom = (org.custom_prompt or "").strip()
            # Strip accidental placeholders to avoid duplication
            if "{context}" in raw_custom or "{question}" in raw_custom or "{conversation_history}" in raw_custom or "{conversation_id}" in raw_custom or "{conversation_context_instruction}" in raw_custom:
                raw_custom = re.sub(r"\{context\}|\{question\}|\{conversation_history\}|\{conversation_id\}|\{conversation_context_instruction\}", "", raw_custom)
            # Fill only benign placeholders (org name, date, etc.)
            instructions = (raw_custom or BASE_INSTRUCTIONS).format_map(SafeDict({
                "organization_name": getattr(org, "name", tenant_id),
                "today": date.today().isoformat(),
                "conversation_id": conversation_id or "new-conversation",
                "conversation_context_instruction": conversation_context_instruction,
            }))
        except Organization.DoesNotExist:
            instructions = BASE_INSTRUCTIONS.format_map(SafeDict({
                "conversation_id": conversation_id or "new-conversation",
                "conversation_context_instruction": conversation_context_instruction,
            }))

        citation_rules = CITATION_RULES if enable_citations else NO_CITATION_RULES

        # Only include a Sources section if citations are enabled and a sources list is provided
        maybe_sources = ""
        if enable_citations and sources.strip():
            maybe_sources = "\nSources (for your internal reference only):\n{sources}\n".format(sources=sources)

        # Enhanced instruction container with conversation history support
        conversation_instruction_container = """{instructions}

{citation_rules}

CONVERSATION CONTEXT:
{conversation_history}

INPUTS
Context:
{context}
{maybe_sources}
Question: {question}
"""

        final_prompt = conversation_instruction_container.format(
            instructions=instructions,
            citation_rules=citation_rules,
            conversation_history=conversation_history or "This is the start of a new conversation.",
            context=context,
            maybe_sources=maybe_sources,
            question=question
        )

        return final_prompt