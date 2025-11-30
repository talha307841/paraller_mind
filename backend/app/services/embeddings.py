"""
Embedding service using sentence-transformers for open-source embeddings.
"""
import os
from typing import List, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        self._embedding_dimension: Optional[int] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded with embedding dimension: {self._model.get_sentence_embedding_dimension()}")
        return self._model
    
    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension of the model."""
        if self._embedding_dimension is None:
            self._embedding_dimension = self.model.get_sentence_embedding_dimension()
        return self._embedding_dimension
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            raise
    
    def embed_numpy(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embedding(s) as numpy array.
        
        Args:
            text: Input text(s) to embed
            
        Returns:
            Numpy array of embedding(s)
        """
        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            embeddings = self.model.encode([text1, text2], convert_to_numpy=True)
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            raise


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name=model_name)
    return _embedding_service
