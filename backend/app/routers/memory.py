"""
Memory API endpoints using FAISS for vector storage and retrieval.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..services.faiss_store import get_faiss_store
from ..services.embeddings import get_embedding_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


# Request/Response models
class MemoryMetadata(BaseModel):
    """Metadata for a memory entry."""
    timestamp: Optional[str] = Field(None, description="ISO timestamp of the memory")
    conversation_id: str = Field(..., description="Unique conversation identifier")
    speaker_id: Optional[str] = Field(None, description="Speaker identifier")
    text: str = Field(..., description="The text content")
    start_time: Optional[float] = Field(None, description="Start time in seconds")
    end_time: Optional[float] = Field(None, description="End time in seconds")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UpsertRequest(BaseModel):
    """Request model for upserting memories."""
    chunks: List[MemoryMetadata] = Field(..., description="List of memory chunks to upsert")
    ids: Optional[List[str]] = Field(None, description="Optional list of unique IDs for each chunk")


class UpsertResponse(BaseModel):
    """Response model for upsert operation."""
    status: str = Field(..., description="Status of the operation")
    vectors_added: int = Field(..., description="Number of vectors added")
    total_vectors: int = Field(..., description="Total vectors in the index")


class SearchRequest(BaseModel):
    """Request model for memory search."""
    query: str = Field(..., description="Query text to search for")
    top_k: int = Field(default=5, description="Number of results to return")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation ID")
    speaker_id: Optional[str] = Field(None, description="Filter by speaker ID")


class SearchResult(BaseModel):
    """Single search result."""
    id: Optional[str] = Field(None, description="Unique ID of the memory")
    text: str = Field(..., description="Text content of the memory")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    metadata: Dict[str, Any] = Field(default={}, description="Metadata of the memory")


class SearchResponse(BaseModel):
    """Response model for memory search."""
    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(default=[], description="Search results")
    total_results: int = Field(..., description="Number of results returned")


class DeleteRequest(BaseModel):
    """Request model for deleting memories."""
    ids: Optional[List[str]] = Field(None, description="List of memory IDs to delete")
    conversation_id: Optional[str] = Field(None, description="Delete all memories for a conversation")


class DeleteResponse(BaseModel):
    """Response model for delete operation."""
    status: str = Field(..., description="Status of the operation")
    deleted: int = Field(..., description="Number of vectors deleted")
    remaining: int = Field(..., description="Remaining vectors in the index")


class StatsResponse(BaseModel):
    """Response model for memory stats."""
    total_vectors: int = Field(..., description="Total vectors in the index")
    dimension: int = Field(..., description="Embedding dimension")
    index_path: str = Field(..., description="Path to the index files")


@router.post("/upsert", response_model=UpsertResponse)
async def upsert_memories(request: UpsertRequest):
    """
    Save transcript chunks into FAISS index.
    
    Each chunk should include:
    - text: The text content
    - conversation_id: Unique conversation identifier
    - timestamp: ISO timestamp (optional)
    - speaker_id: Speaker identifier (optional)
    """
    try:
        if not request.chunks:
            raise HTTPException(status_code=400, detail="chunks list cannot be empty")
        
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        
        # Extract texts for batch embedding
        texts = [chunk.text for chunk in request.chunks]
        
        # Generate embeddings in batch
        embeddings = embedding_service.embed_batch(texts)
        
        # Prepare metadata
        metadata_list = []
        for chunk in request.chunks:
            meta = {
                "text": chunk.text,
                "conversation_id": chunk.conversation_id,
                "timestamp": chunk.timestamp or datetime.utcnow().isoformat(),
                "speaker_id": chunk.speaker_id,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time
            }
            if chunk.extra:
                meta.update(chunk.extra)
            metadata_list.append(meta)
        
        # Upsert to FAISS
        result = faiss_store.upsert(
            vectors=embeddings,
            metadata=metadata_list,
            ids=request.ids
        )
        
        return UpsertResponse(
            status=result["status"],
            vectors_added=result["vectors_added"],
            total_vectors=result["total_vectors"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upsert error: {e}")
        raise HTTPException(status_code=500, detail=f"Memory upsert failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """
    Search FAISS index for relevant memories.
    
    Returns top-k similar memories based on semantic similarity
    to the query text.
    """
    try:
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        
        # Generate query embedding
        query_embedding = embedding_service.embed(request.query)
        
        # Build filter
        filter_metadata = {}
        if request.conversation_id:
            filter_metadata["conversation_id"] = request.conversation_id
        if request.speaker_id:
            filter_metadata["speaker_id"] = request.speaker_id
        
        # Search FAISS
        results = faiss_store.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        # Convert to response model
        search_results = [
            SearchResult(
                id=r.get("id"),
                text=r.get("text", ""),
                similarity_score=r.get("similarity_score", 0),
                metadata=r.get("metadata", {})
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results)
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")


@router.delete("/delete", response_model=DeleteResponse)
async def delete_memories(request: DeleteRequest):
    """
    Delete memories from the FAISS index.
    
    Can delete by specific IDs or by conversation_id.
    """
    try:
        if not request.ids and not request.conversation_id:
            raise HTTPException(
                status_code=400,
                detail="Must provide either ids or conversation_id"
            )
        
        faiss_store = get_faiss_store()
        
        filter_metadata = None
        if request.conversation_id:
            filter_metadata = {"conversation_id": request.conversation_id}
        
        result = faiss_store.delete(
            ids=request.ids,
            filter_metadata=filter_metadata
        )
        
        return DeleteResponse(
            status=result["status"],
            deleted=result["deleted"],
            remaining=result.get("remaining", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=f"Memory deletion failed: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_memory_stats():
    """
    Get statistics about the memory index.
    """
    try:
        faiss_store = get_faiss_store()
        stats = faiss_store.get_stats()
        
        return StatsResponse(
            total_vectors=stats["total_vectors"],
            dimension=stats["dimension"],
            index_path=stats["index_path"]
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/clear")
async def clear_memory():
    """
    Clear all memories from the index.
    
    WARNING: This operation cannot be undone.
    """
    try:
        faiss_store = get_faiss_store()
        faiss_store.clear()
        
        return {"status": "success", "message": "All memories cleared"}
        
    except Exception as e:
        logger.error(f"Clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear memories: {str(e)}")
