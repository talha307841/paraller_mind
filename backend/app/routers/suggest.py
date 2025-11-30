"""
Suggest API endpoint for RAG-based suggestions using FAISS and Ollama.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..services.faiss_store import get_faiss_store
from ..services.embeddings import get_embedding_service
from ..services.ollama_client import get_ollama_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggest", tags=["suggest"])


# Request/Response models
class SourceReference(BaseModel):
    """Reference to a source memory."""
    id: Optional[str] = Field(None, description="Source memory ID")
    text: str = Field(..., description="Source text content")
    similarity_score: float = Field(..., description="Similarity to the query")
    conversation_id: Optional[str] = Field(None, description="Source conversation ID")
    speaker_id: Optional[str] = Field(None, description="Source speaker ID")


class SuggestRequest(BaseModel):
    """Request model for generating suggestions."""
    text: str = Field(..., description="Latest transcript chunk or query text")
    conversation_id: Optional[str] = Field(None, description="Filter memories by conversation ID")
    top_k: int = Field(default=5, description="Number of memory results to retrieve")
    model: Optional[str] = Field(None, description="Ollama model to use (defaults to llama3)")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt for the LLM")
    temperature: float = Field(default=0.7, description="LLM temperature (0-1)")


class SuggestResponse(BaseModel):
    """Response model for suggestions."""
    suggestion: str = Field(..., description="Generated suggestion text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    sources: List[SourceReference] = Field(default=[], description="Source references used")
    model: str = Field(..., description="Model used for generation")
    query: str = Field(..., description="Original query text")


class RagContext(BaseModel):
    """Context information for RAG."""
    retrieved_memories: List[SourceReference] = Field(default=[], description="Retrieved memories")
    prompt_used: str = Field(..., description="Full prompt sent to LLM")


class SuggestDetailedResponse(BaseModel):
    """Detailed response model with RAG context."""
    suggestion: str = Field(..., description="Generated suggestion text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    sources: List[SourceReference] = Field(default=[], description="Source references used")
    model: str = Field(..., description="Model used for generation")
    query: str = Field(..., description="Original query text")
    rag_context: RagContext = Field(..., description="RAG context information")


def build_rag_prompt(
    query: str,
    context_memories: List[Dict[str, Any]],
    custom_system_prompt: Optional[str] = None
) -> tuple[str, str]:
    """Build the RAG prompt with retrieved context."""
    
    # Format context from memories
    context_parts = []
    for i, mem in enumerate(context_memories, 1):
        text = mem.get("text", "")
        speaker = mem.get("metadata", {}).get("speaker_id", "Unknown")
        context_parts.append(f"[{i}] {speaker}: {text}")
    
    context_text = "\n".join(context_parts) if context_parts else "No relevant context found."
    
    system_prompt = custom_system_prompt or """You are a helpful AI assistant that provides contextual suggestions based on conversation history. 
Your task is to analyze the conversation context and provide a relevant, helpful suggestion or response.
Be concise, clear, and directly address the user's needs based on the context provided.
If the context is not sufficient, acknowledge this and provide the best suggestion you can."""

    user_prompt = f"""Based on the following conversation context, provide a helpful suggestion or response.

CONTEXT:
{context_text}

CURRENT INPUT:
{query}

Please provide:
1. A clear, actionable suggestion or response
2. Reference specific parts of the context if relevant

Your suggestion:"""

    return system_prompt, user_prompt


@router.post("", response_model=SuggestResponse)
async def generate_suggestion(request: SuggestRequest):
    """
    Generate a suggestion using RAG (Retrieval-Augmented Generation).
    
    Flow:
    1. Embed the latest transcript chunk
    2. Search FAISS for top-k relevant memories
    3. Prepare prompt with retrieved context
    4. Send to Llama model via Ollama
    5. Return suggestion with confidence and source references
    """
    try:
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        ollama_client = get_ollama_client()
        
        # Step 1: Embed the query text
        query_embedding = embedding_service.embed(request.text)
        
        # Step 2: Search FAISS for relevant memories
        filter_metadata = {}
        if request.conversation_id:
            filter_metadata["conversation_id"] = request.conversation_id
        
        search_results = faiss_store.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        # Step 3: Build RAG prompt
        system_prompt, user_prompt = build_rag_prompt(
            query=request.text,
            context_memories=search_results,
            custom_system_prompt=request.system_prompt
        )
        
        # Step 4: Call Ollama
        model = request.model or "llama3"
        
        try:
            # Check if Ollama is available
            is_healthy = await ollama_client.health_check()
            if not is_healthy:
                raise HTTPException(
                    status_code=503,
                    detail="Ollama service is not available. Please ensure Ollama is running."
                )
            
            response = await ollama_client.generate(
                prompt=user_prompt,
                model=model,
                system=system_prompt,
                options={
                    "temperature": request.temperature,
                    "top_p": 0.9
                }
            )
            
            suggestion_text = response.get("response", "")
            
            # Calculate confidence based on context similarity and response
            avg_similarity = sum(r.get("similarity_score", 0) for r in search_results) / max(len(search_results), 1)
            confidence = min(avg_similarity, 0.99)  # Cap at 0.99
            
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}. Returning fallback response.")
            suggestion_text = "Unable to generate suggestion. Please ensure Ollama is running with the specified model."
            confidence = 0.0
        
        # Step 5: Build source references
        sources = [
            SourceReference(
                id=r.get("id"),
                text=r.get("text", ""),
                similarity_score=r.get("similarity_score", 0),
                conversation_id=r.get("metadata", {}).get("conversation_id"),
                speaker_id=r.get("metadata", {}).get("speaker_id")
            )
            for r in search_results
        ]
        
        return SuggestResponse(
            suggestion=suggestion_text,
            confidence=confidence,
            sources=sources,
            model=model,
            query=request.text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Suggestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")


@router.post("/detailed", response_model=SuggestDetailedResponse)
async def generate_suggestion_detailed(request: SuggestRequest):
    """
    Generate a suggestion with detailed RAG context information.
    
    Same as /suggest but includes the full RAG context for debugging
    and transparency.
    """
    try:
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        ollama_client = get_ollama_client()
        
        # Step 1: Embed the query text
        query_embedding = embedding_service.embed(request.text)
        
        # Step 2: Search FAISS for relevant memories
        filter_metadata = {}
        if request.conversation_id:
            filter_metadata["conversation_id"] = request.conversation_id
        
        search_results = faiss_store.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        # Step 3: Build RAG prompt
        system_prompt, user_prompt = build_rag_prompt(
            query=request.text,
            context_memories=search_results,
            custom_system_prompt=request.system_prompt
        )
        
        full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
        
        # Step 4: Call Ollama
        model = request.model or "llama3"
        
        try:
            is_healthy = await ollama_client.health_check()
            if not is_healthy:
                raise HTTPException(
                    status_code=503,
                    detail="Ollama service is not available. Please ensure Ollama is running."
                )
            
            response = await ollama_client.generate(
                prompt=user_prompt,
                model=model,
                system=system_prompt,
                options={
                    "temperature": request.temperature,
                    "top_p": 0.9
                }
            )
            
            suggestion_text = response.get("response", "")
            avg_similarity = sum(r.get("similarity_score", 0) for r in search_results) / max(len(search_results), 1)
            confidence = min(avg_similarity, 0.99)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            suggestion_text = "Unable to generate suggestion. Please ensure Ollama is running."
            confidence = 0.0
        
        # Build source references
        sources = [
            SourceReference(
                id=r.get("id"),
                text=r.get("text", ""),
                similarity_score=r.get("similarity_score", 0),
                conversation_id=r.get("metadata", {}).get("conversation_id"),
                speaker_id=r.get("metadata", {}).get("speaker_id")
            )
            for r in search_results
        ]
        
        return SuggestDetailedResponse(
            suggestion=suggestion_text,
            confidence=confidence,
            sources=sources,
            model=model,
            query=request.text,
            rag_context=RagContext(
                retrieved_memories=sources,
                prompt_used=full_prompt
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detailed suggestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")


@router.get("/health")
async def check_suggestion_health():
    """Check the health of suggestion dependencies."""
    try:
        ollama_client = get_ollama_client()
        ollama_healthy = await ollama_client.health_check()
        
        faiss_store = get_faiss_store()
        faiss_stats = faiss_store.get_stats()
        
        return {
            "status": "healthy" if ollama_healthy else "degraded",
            "ollama": {
                "status": "available" if ollama_healthy else "unavailable",
                "host": ollama_client.host,
                "model": ollama_client.model
            },
            "faiss": {
                "status": "available",
                "total_vectors": faiss_stats["total_vectors"]
            }
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
