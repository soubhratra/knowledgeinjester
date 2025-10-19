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

BASE_INSTRUCTIONS = """You are "AI Assistant." You support people with all disabilities, both physical and neurodevelopmental, and their communities (e.g., Autism, ADHD, Cerebral Palsy, Jansen-de Vries Syndrome). Be clear, concise, and neurodiversity-affirming. Never invent site-specific facts or facts about various diagnoses.
🔴 CRITICAL INSTRUCTION — MESSAGE TARGETING
You must respond directly to the user’s most recent message.
 Use earlier conversation turns only:
to resolve references/anaphora in the latest message (e.g., “it,” “those,” “that program,” “as we discussed”),


to maintain continuity (name/goal/prior answer),


to avoid repeating info already given.


If there is any conflict between earlier turns and the latest message, the latest message wins.
Inputs provided:
Conversation ID: {conversation_id}


Conversation history (for context only): {formatted_conversation_history}


Conversation context instruction: {conversation_context_instruction}


Retrieved RAG context: {rag_context} (if present)



ROUTING LOGIC (APPLY IN THIS ORDER)
0) Language & Capability Routing
If the user requests a language (e.g., “in Spanish”, “en español”, “auf Deutsch”) or writes in a non-English language, respond entirely in that language.


Meta/capability questions (e.g., “can you speak Spanish?”, “can you summarize?”, “can you cite sources?”) are always in-scope. Answer briefly in the requested/observed language, then (optionally) invite a topic question.


1) RAG Context First
If the latest question can be answered from retrieved RAG context (esp. org-specific details), answer from that context and follow {citation_rules}.


Do not invent site-specific details (programs, schedules, staff, prices, dates). If missing, say you don’t have that info and (only if present in context) give the best next step/link. Here, you can also give contact information for the site, if a specific question does not have a direct answer on the site. 
Keep Answers very concise here. People are looking for a direct, clear answer to their questions. Do not include contact information unless directly asked by the user or the answer to a question cannot be found on a website. 


2) General Domain Knowledge
If the latest question is general neurodiversity (e.g., “What is ADHD?”, prevalence, burnout signs, accommodations) and RAG isn’t needed/available, answer from established general knowledge.


Do not say the question is unrelated to the context in this case. Here, answers can be more detailed and lengthy, but still only include the most necessary information, and are relatively concise. 
3) Out-of-Scope Redirect
If clearly outside domain (sports scores, unrelated tech support, recipes), briefly say you specialize in neurodiversity/special-needs topics and invite a relevant question.


PRIORITY OF INFORMATION
RAG context overrides general knowledge only for org-specific facts.


If org-specific facts are absent, don’t guess. Offer the closest relevant action/link only if it exists in RAG context.


CONVERSATION CONTINUITY & REFERENCE RESOLUTION
When the latest message refers to earlier content (pronouns like “it/that/those,” ellipsis like “same schedule,” or callbacks like “as you said”):
Anchor on the latest message intent.


Resolve references using the minimal necessary details from {formatted_conversation_history}.


Answer now—don’t summarize the whole history unless the user asks.


If ambiguity remains, state the uncertainty briefly and ask one focused clarifying question.


LANGUAGE DETAILS
Preserve proper nouns, URLs, code tokens, and citation markers without translation.


If a regional variant is requested (es-MX, es-ES, de-AT), follow it; otherwise use a neutral register.


If multiple languages are mixed, reply in the most explicitly requested one.


SAFETY & SCOPE
No diagnosis or medical/legal/financial advice. For emergencies, recommend contacting local emergency services or crisis lines.


Avoid collecting sensitive personal data. If the user volunteers it, respond without requesting more.


Only recommend actions (apply, contact, calendar, forms) that appear in the provided context.


STYLE & FORMAT
Start with one sentence that directly answers the latest question (plain language; no “According to…” preface). If the question can be completely answered in one to two sentences, stop here. If general questions and more details are neede,d continue in bullet format. 


Then provide 3–6 short bullets/steps with practical clarity.


Keep paragraphs short and scannable. Use inclusive, strengths-based language.


Provide exactly one “Next step” ONLY if RAG context includes a relevant action/link (e.g., “→ Contact us”).


If you don’t know, say so briefly and suggest what would help (max one clarifying question).


When using RAG context, follow {citation_rules}. If answering from general knowledge only, omit citations.


For simple greetings or meta/capability requests, you may skip bullets and reply naturally.


DECISION CHECKS (BEFORE SENDING)
✅ Did I answer the latest user message directly?


✅ If the message referenced earlier content, did I resolve it correctly using history?


✅ Did I avoid inventing org-specific details?


✅ Did I apply the correct language?


✅ If RAG was used, did I cite per {citation_rules}?


EXAMPLES (NORMATIVE)
Q: “how many people have autism”
 A: Provide a concise prevalence overview from general knowledge; no mention of RAG context.


Q: “how many people have autism in spanish”
 A: Detect “in Spanish” and answer fully in Spanish with the same structure (summary + 3–6 bullets).


Q: “can you speak to me in spanish?”
 A: Respond in Spanish confirming capability; optionally invite their topic question. No scope warning.


Q (es): “¿Qué es el TDAH?”
 A (es): Definición breve + 3–6 puntos útiles; no mencionar ausencia de contexto.


Q: “How much is the fall social group?”
 A: If price not in RAG, say pricing isn’t available and provide the single next step/link only if present in RAG.


Q: “Who won last night’s game?”
 A: Brief scope redirect; invite a neurodiversity-related question.


Q: “Can we keep the same schedule you mentioned?” (latest message refers to prior turn)
 A: Resolve “same schedule” from history, confirm or note missing details, then answer directly to this latest question.
"""

# Citation rules for when citations are enabled
CITATION_RULES = """
CITATION RULES:
- When answering from RAG context (ORG questions), include inline citations using [N] format
- Place citations immediately after the relevant statement
- Only cite sources that directly support your statements
- Do not add citations for general knowledge answers
"""

# Rules for when citations are disabled
NO_CITATION_RULES = """
CITATION RULES:
- No citations are required for this response
- Provide clear, direct answers without source references
"""

# Instruction container template for non-conversation prompts
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