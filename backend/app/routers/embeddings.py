"""
Embeddings API endpoint using sentence-transformers.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from ..services.embeddings import get_embedding_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


# Request/Response models
class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    text: str = Field(..., description="Text to generate embedding for")


class EmbeddingBatchRequest(BaseModel):
    """Request model for batch embedding generation."""
    texts: List[str] = Field(..., description="List of texts to generate embeddings for")


class EmbeddingResponse(BaseModel):
    """Response model for embedding."""
    embedding: List[float] = Field(..., description="Embedding vector")
    dimension: int = Field(..., description="Dimension of the embedding")
    model: str = Field(default="all-MiniLM-L6-v2", description="Model used for embedding")


class EmbeddingBatchResponse(BaseModel):
    """Response model for batch embeddings."""
    embeddings: List[List[float]] = Field(..., description="List of embedding vectors")
    dimension: int = Field(..., description="Dimension of each embedding")
    model: str = Field(default="all-MiniLM-L6-v2", description="Model used for embedding")
    count: int = Field(..., description="Number of embeddings generated")


class SimilarityRequest(BaseModel):
    """Request model for similarity calculation."""
    text1: str = Field(..., description="First text")
    text2: str = Field(..., description="Second text")


class SimilarityResponse(BaseModel):
    """Response model for similarity."""
    similarity: float = Field(..., description="Cosine similarity score (0-1)")
    text1: str = Field(..., description="First text")
    text2: str = Field(..., description="Second text")


@router.post("", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """
    Generate embedding for a single text.
    
    Uses sentence-transformers "all-MiniLM-L6-v2" model to generate
    a 384-dimensional embedding vector.
    """
    try:
        service = get_embedding_service()
        embedding = service.embed(request.text)
        
        return EmbeddingResponse(
            embedding=embedding,
            dimension=len(embedding),
            model=service.model_name
        )
        
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@router.post("/batch", response_model=EmbeddingBatchResponse)
async def generate_embeddings_batch(request: EmbeddingBatchRequest):
    """
    Generate embeddings for multiple texts in batch.
    
    More efficient than calling the single endpoint multiple times.
    """
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="texts list cannot be empty")
        
        service = get_embedding_service()
        embeddings = service.embed_batch(request.texts)
        
        return EmbeddingBatchResponse(
            embeddings=embeddings,
            dimension=len(embeddings[0]) if embeddings else 0,
            model=service.model_name,
            count=len(embeddings)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch embedding generation failed: {str(e)}")


@router.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """
    Calculate cosine similarity between two texts.
    
    Returns a similarity score between 0 and 1, where 1 means identical
    semantic meaning and 0 means completely different.
    """
    try:
        service = get_embedding_service()
        similarity = service.similarity(request.text1, request.text2)
        
        return SimilarityResponse(
            similarity=similarity,
            text1=request.text1,
            text2=request.text2
        )
        
    except Exception as e:
        logger.error(f"Similarity calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Similarity calculation failed: {str(e)}")


@router.get("/info")
async def get_embedding_info():
    """Get information about the embedding model."""
    try:
        service = get_embedding_service()
        return {
            "model": service.model_name,
            "dimension": service.embedding_dimension,
            "status": "ready"
        }
    except Exception as e:
        logger.error(f"Info error: {e}")
        return {
            "model": "all-MiniLM-L6-v2",
            "dimension": 384,
            "status": "not_loaded",
            "error": str(e)
        }
