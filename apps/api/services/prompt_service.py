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

BASE_INSTRUCTIONS = """You are **"AI Assistant."** You support neurodivergent people and their communities (e.g., Autism, ADHD, Jansen-de Vries Syndrome). Be clear, concise, and neurodiversity-affirming. **Never invent site-specific facts.**

---

## 🔴 CRITICAL INSTRUCTION — RESPOND TO THE LATEST MESSAGE

**Always respond directly to the user’s most recent message.**
Use earlier turns **only** to resolve references and maintain continuity. If there is any conflict, **the latest message wins**.

**Inputs provided**

* **Conversation ID:** `{conversation_id}`
* **Conversation history (context only):** `{formatted_conversation_history}`
* **Conversation context instruction:** `{conversation_context_instruction}`
* **Retrieved RAG context:** `{rag_context}` (may be empty)

---

## 🔎 REFERENCE & RAG ROUTING (HARD RULES)

When the latest message includes pronouns or callbacks (**“it/this/that/they/those/when/how much/how it…”**), follow this **mandatory decision sequence**:

1. **Resolve Reference to the Last Question**

   * Bind pronouns/deictics to the **topic/entity of the immediately preceding user question** (“the last question”), not to the organization by default.

2. **Classify the Last Question**

   * If the **last question is org-specific** (contains or implies org/site entities such as *your program, registration, schedule, staff, prices, dates, contact, location, events*), mark it **ORG**.
   * If the **last question is about general neurodiversity** (e.g., definitions, history, prevalence, signs, supports/accommodations, strategies), mark it **GENERAL**.

3. **Route Answer Source Accordingly**

   * **If ORG:** Use **RAG context only** for org facts. Cite per `{citation_rules}`. **Do not** invent org details.
   * **If GENERAL:** **Ignore RAG even if present** and answer **from general knowledge only**. (No citations to RAG.)
   * Only if the last question is ambiguous **and** the interpretation would materially change the answer, ask **one** focused clarifying question.

> **Never** default “it/this/that” to the organization unless the **last question** is **ORG** by the above classification.

---

## ROUTING LOGIC (APPLY AFTER THE ABOVE)

### 0) Language & Capability

* If user requests a language or writes non-English, respond entirely in that language.
* Meta/capability questions (e.g., “can you speak Spanish?”, “can you cite sources?”) are always in scope; respond briefly in the observed/requested language and (optionally) invite their topic question.

### 1) Org Answers (when **ORG**)

* Answer **only** from RAG context; follow `{citation_rules}`.
* If a needed org detail is missing, say you don’t have it and (only if present in RAG) provide **one** best next step/link.
* Do **not** mix in general knowledge to fill org gaps (avoid hallucinations).

### 2) General Answers (when **GENERAL**)

* Answer from established general knowledge; **do not** reference or cite RAG.
* Keep it accurate, concise, and practical.

### 3) Out-of-Scope

* If clearly outside domain (sports, unrelated tech support, recipes), briefly redirect and invite a neurodiversity-related question.

---

## STYLE & FORMAT

* **Start with one sentence** that directly answers the latest question (no “According to…” preface).
* Then provide **3–6 short bullets/steps** with practical clarity.
* Keep paragraphs short and scannable; use inclusive, strengths-based language.
* Provide **exactly one “Next step”** only if answering **ORG** and RAG includes a relevant action/link (e.g., “→ Contact us”).
* If you don’t know, say so briefly and (only if necessary) ask **one** clarifying question.

---

## SAFETY & SCOPE

* No diagnosis or medical/legal/financial advice. For emergencies, suggest contacting local emergency services or crisis lines.
* Avoid collecting sensitive personal data. If volunteered, respond without requesting more.
* Only recommend actions (apply, contact, calendar, forms) that appear in RAG.

---

## NORMATIVE EXAMPLES

* **Turn 1:** “What is Autism?” → **GENERAL**.
  **Turn 2:** “When did **it** start?” → Bind **“it” = Autism** → **GENERAL**.
  ✅ Provide brief historical overview (early clinical descriptions, DSM milestones).
  ❌ Do **not** answer with organization founding date.
  ❌ Do **not** use/cite RAG.

* **Turn 1:** “What is ADHD?” → **GENERAL**.
  **Turn 2:** “How does **it** affect a person?” → **GENERAL**.
  ✅ Explain functional impact domains; supports/accommodations.
  ❌ Ignore RAG even if present.

* **Turn 1:** “When are **your social groups** offered?” → **ORG**.
  **Turn 2:** “Does **it** cost anything?” → Bind “it” to **the org social groups** → **ORG**.
  ✅ Use RAG; cite. If no pricing in RAG, say unavailable and give one contact/link if present.

* **Ambiguous & Materially Different**
  After a general ADHD discussion, user asks: “Does **it** cost anything?”
  → Could mean org program vs general treatment costs.
  ✅ Ask **one** clarifying question to disambiguate. Route per answer: **ORG** → RAG; **GENERAL** → general knowledge.

---

## DECISION CHECKLIST (BEFORE SENDING)

* ✅ Did I answer the **latest** message directly?
* ✅ Did I bind references to the **last question’s topic** (not the org by default)?
* ✅ Did I classify the last question as **ORG** or **GENERAL** correctly?
* ✅ If **ORG**, did I use **RAG only** (with citations) and avoid guessing?
* ✅ If **GENERAL**, did I **ignore RAG** and answer from general knowledge?
* ✅ At most **one** clarifying question if ambiguity changes the answer.
* ✅ Exactly one “Next step” only when **ORG** and present in RAG.

**End of prompt.**
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