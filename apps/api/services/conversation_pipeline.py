from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from openai import OpenAI
from django.conf import settings
import logging
import time
import uuid
from typing import Annotated
from langgraph.graph.message import add_messages
from .conversation_storage import conversation_storage

logger = logging.getLogger('apps.api')

class ConversationState(TypedDict):
    """State for conversation pipeline with history support"""
    messages: Annotated[List[Dict[str, str]], add_messages]
    tenant_id: str
    enable_citations: bool
    context: str
    sources: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    conversation_id: Optional[str]

class ConversationPipeline:
    """Enhanced conversation pipeline with LangGraph and conversation history"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = MemorySaver()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the conversation graph with history support"""
        g = StateGraph(ConversationState)
        
        # Add nodes
        g.add_node("retrieve_context", self._retrieve_context_node)
        g.add_node("generate_response", self._generate_response_node)
        g.add_node("process_citations", self._process_citations_node)
        
        # Set up the flow
        g.set_entry_point("retrieve_context")
        g.add_edge("retrieve_context", "generate_response")
        g.add_edge("generate_response", "process_citations")
        g.add_edge("process_citations", END)
        
        return g.compile(checkpointer=self.memory)
    
    def _retrieve_context_node(self, state: ConversationState) -> ConversationState:
        """Retrieve relevant context for the conversation"""
        try:
            # Import here to avoid circular imports
            from apps.vectorizer.embedder import embed_texts
            from apps.vectorizer.supabase_store import hybrid_search
            from apps.api.services.prompt_service import PromptService
            from langchain_core.messages import HumanMessage, AIMessage
            
            # Get the latest user message - handle both dict and LangGraph message objects
            user_messages = []
            for msg in state["messages"]:
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        user_messages.append(msg)
                elif isinstance(msg, HumanMessage):
                    user_messages.append({"role": "user", "content": msg.content})
            
            if not user_messages:
                return state
            
            question = user_messages[-1]["content"]
            
            # Embed the question
            qvec = embed_texts([question])[0]
            
            # Retrieve context
            top_k = getattr(settings, "RETRIEVAL_TOP_K", 6)
            hits = hybrid_search(
                tenant_id=state["tenant_id"],
                query=question,
                query_vec=qvec,
                top_k=top_k
            )
            
            # Format context in the original working format
            context_parts = []
            for i, hit in enumerate(hits, 1):
                title = hit.get('title', '')
                content = hit.get('text', '')  # Use 'text' field from hybrid search results
                source_url = hit.get('source_url', '')
                
                context_part = f"[{i}]"
                if title:
                    context_part += f" {title}"
                if source_url:
                    context_part += f" (Source: {source_url})"
                context_part += f"\n{content}"
                
                context_parts.append(context_part)
            
            context = "\n\n".join(context_parts)
            
            # Log context for debugging
            logger.info("Retrieved context for conversation", extra={
                'conversation_id': state.get('conversation_id'),
                'tenant_id': state["tenant_id"],
                'hits_count': len(hits),
                'context_length': len(context),
                'context_preview': context[:1000] + "..." if len(context) > 1000 else context,
                'question': question
            })
            
            # Also log each hit individually for debugging
            for i, hit in enumerate(hits):
                logger.info(f"Hit {i+1} details", extra={
                    'title': hit.get('title', ''),
                    'content_preview': hit.get('content', '')[:200] + "..." if len(hit.get('content', '')) > 200 else hit.get('content', ''),
                    'source_url': hit.get('source_url', ''),
                    'score': hit.get('score', 0)
                })
            
            # Context retrieval is complete - no need to generate prompt here
            # The prompt will be generated in generate_response_node using the retrieved context
            
            # Debug: Log the context being stored
            logger.info("Storing context in retrieve_context_node", extra={
                'context_length': len(context),
                'context_preview': context[:200] + "..." if len(context) > 200 else context,
                'hits_count': len(hits)
            })
            
            return {
                **state,
                "context": context,
                "sources": hits
            }
            
        except Exception as e:
            logger.error(f"Error in retrieve_context_node: {str(e)}")
            return state
    
    def _generate_response_node(self, state: ConversationState) -> ConversationState:
        """Generate response using conversation history and context"""
        try:
            from langchain_core.messages import HumanMessage, AIMessage
            
            # Get the latest user message - handle both dict and LangGraph message objects
            user_messages = []
            for msg in state["messages"]:
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        user_messages.append(msg)
                elif isinstance(msg, HumanMessage):
                    user_messages.append({"role": "user", "content": msg.content})
            
            if not user_messages:
                return state
            
            question = user_messages[-1]["content"]
            
            # Use the original prompt service approach but with conversation history
            from apps.api.services.prompt_service import PromptService
            
            # Build conversation history string - handle both dict and LangGraph message objects
            conversation_history = ""
            for msg in state["messages"][:-1]:  # Exclude the current question
                if isinstance(msg, dict):
                    role = msg["role"]
                    content = msg["content"]
                elif isinstance(msg, HumanMessage):
                    role = "user"
                    content = msg.content
                elif isinstance(msg, AIMessage):
                    role = "assistant"
                    content = msg.content
                else:
                    continue  # Skip unknown message types
                
                conversation_history += f"{role.title()}: {content}\n"
            
            # Debug: Log the context being used
            context = state.get('context', '')
            logger.info("Using context in generate_response_node", extra={
                'context_length': len(context),
                'context_preview': context[:200] + "..." if len(context) > 200 else context,
                'question': question
            })
            
            # Use the original prompt service with conversation history
            prompt_service = PromptService()
            prompt = prompt_service.get_conversation_prompt_for_organization(
                tenant_id=state["tenant_id"],
                enable_citations=state["enable_citations"],
                context=context,
                question=question,
                sources="",  # Will be filled in process_citations_node
                conversation_history=conversation_history.strip(),
                conversation_id=state.get("conversation_id", ""),
                new_conversation=state.get("is_new_conversation", False)
            )
            
            # Use the original single message approach that was working
            messages = [{"role": "user", "content": prompt}]
            
            # Call LLM
            resp = self.client.chat.completions.create(
                model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )
            
            answer = resp.choices[0].message.content
            
            return {
                **state,
                "answer": answer
            }
            
        except Exception as e:
            logger.error(f"Error in generate_response_node: {str(e)}")
            return state
    
    def _process_citations_node(self, state: ConversationState) -> ConversationState:
        """Process citations if enabled"""
        try:
            if not state.get("enable_citations", True) or not state.get("sources"):
                return state
            
            # Import here to avoid circular imports
            from apps.api.router import process_citations
            
            # Process citations
            source_objects, processed_answer = process_citations(
                state["sources"], 
                state["answer"], 
                enable_citations=True
            )
            
            return {
                **state,
                "answer": processed_answer,
                "sources": source_objects
            }
            
        except Exception as e:
            logger.error(f"Error in process_citations_node: {str(e)}")
            return state
    
    def process_conversation(
        self, 
        user_message: str,
        tenant_id: str, 
        enable_citations: bool = True,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation with history support using server-side storage
        
        Args:
            user_message: The user's current message
            tenant_id: Tenant identifier
            enable_citations: Whether to include citations
            conversation_id: Optional conversation ID for existing conversation
            
        Returns:
            Dictionary with answer, sources, and conversation_id
        """
        try:
            # Get or create conversation
            is_new_conversation = False
            if conversation_id:
                # Retrieve existing conversation
                conversation = conversation_storage.get_conversation(conversation_id, tenant_id)
                if conversation is None:
                    logger.warning("Conversation not found, creating new one", extra={
                        'conversation_id': conversation_id,
                        'tenant_id': tenant_id
                    })
                    conversation = conversation_storage.create_conversation(conversation_id, tenant_id)
                    is_new_conversation = True
            else:
                # Create new conversation
                conversation_id = f"conv_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                conversation = conversation_storage.create_conversation(conversation_id, tenant_id)
                is_new_conversation = True
            
            # Add user message to conversation
            conversation_storage.add_message(conversation_id, tenant_id, "user", user_message)
            
            # Get all messages for the conversation
            messages = conversation_storage.get_conversation_messages(conversation_id, tenant_id)
            
            # Prepare initial state
            initial_state = {
                "messages": messages,
                "tenant_id": tenant_id,
                "enable_citations": enable_citations,
                "context": "",
                "sources": None,
                "answer": None,
                "conversation_id": conversation_id,
                "is_new_conversation": is_new_conversation
            }
            
            # Run the graph
            config = {"configurable": {"thread_id": conversation_id}}
            result = self.graph.invoke(initial_state, config=config)
            
            # Add assistant response to conversation
            if result.get("answer"):
                conversation_storage.add_message(conversation_id, tenant_id, "assistant", result["answer"])
            
            return {
                "answer": result.get("answer", ""),
                "sources": result.get("sources"),
                "conversation_id": conversation_id,
                "context": result.get("context", "")
            }
            
        except Exception as e:
            logger.error(f"Error processing conversation: {str(e)}")
            return {
                "answer": "I apologize, but I encountered an error processing your request.",
                "sources": None,
                "conversation_id": conversation_id,
                "context": ""
            }

# Global instance
conversation_pipeline = ConversationPipeline()
