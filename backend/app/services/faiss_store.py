"""
FAISS-based vector store for open-source semantic search.
"""
import os
import json
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
import logging
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


class FAISSStore:
    """FAISS-based vector store for memory storage and retrieval."""
    
    def __init__(
        self,
        dimension: int = 384,  # all-MiniLM-L6-v2 dimension
        index_path: str = "./faiss_index",
        use_gpu: bool = False
    ):
        """
        Initialize the FAISS store.
        
        Args:
            dimension: Dimension of embedding vectors
            index_path: Path to persist the index
            use_gpu: Whether to use GPU (requires faiss-gpu)
        """
        self.dimension = dimension
        self.index_path = index_path
        self.use_gpu = use_gpu
        self._index: Optional[faiss.IndexFlatIP] = None
        self._metadata: List[Dict[str, Any]] = []
        self._lock = Lock()
        
        # Ensure index directory exists
        os.makedirs(index_path, exist_ok=True)
        
        # Load existing index if available
        self._load_index()
    
    @property
    def index(self) -> faiss.IndexFlatIP:
        """Get or create the FAISS index."""
        if self._index is None:
            # Use IndexFlatIP for cosine similarity (after L2 normalization)
            self._index = faiss.IndexFlatIP(self.dimension)
            logger.info(f"Created new FAISS index with dimension {self.dimension}")
        return self._index
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine similarity."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return vectors / norms
    
    def _load_index(self):
        """Load index from disk if available."""
        index_file = os.path.join(self.index_path, "faiss.index")
        metadata_file = os.path.join(self.index_path, "metadata.pkl")
        
        try:
            if os.path.exists(index_file) and os.path.exists(metadata_file):
                self._index = faiss.read_index(index_file)
                with open(metadata_file, "rb") as f:
                    self._metadata = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
        except Exception as e:
            logger.warning(f"Could not load existing index: {e}")
            self._index = None
            self._metadata = []
    
    def _save_index(self):
        """Save index to disk."""
        if self._index is None:
            return
            
        index_file = os.path.join(self.index_path, "faiss.index")
        metadata_file = os.path.join(self.index_path, "metadata.pkl")
        
        try:
            faiss.write_index(self._index, index_file)
            with open(metadata_file, "wb") as f:
                pickle.dump(self._metadata, f)
            logger.info(f"Saved FAISS index with {self._index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def upsert(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Insert or update vectors with metadata.
        
        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries (must include timestamp, conversation_id, speaker_id)
            ids: Optional list of unique IDs for the vectors
            
        Returns:
            Dictionary with upsert result info
        """
        with self._lock:
            try:
                vectors_np = np.array(vectors, dtype=np.float32)
                vectors_np = self._normalize(vectors_np)
                
                # Generate IDs if not provided
                if ids is None:
                    base_idx = len(self._metadata)
                    ids = [f"vec_{base_idx + i}" for i in range(len(vectors))]
                
                # Add vectors to index
                self.index.add(vectors_np)
                
                # Store metadata with vector index
                for i, (vec_id, meta) in enumerate(zip(ids, metadata)):
                    meta_entry = {
                        "id": vec_id,
                        "index": len(self._metadata),
                        **meta
                    }
                    self._metadata.append(meta_entry)
                
                # Persist to disk
                self._save_index()
                
                return {
                    "status": "success",
                    "vectors_added": len(vectors),
                    "total_vectors": self.index.ntotal
                }
                
            except Exception as e:
                logger.error(f"Upsert error: {e}")
                raise
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"conversation_id": "123"})
            
        Returns:
            List of results with metadata and similarity scores
        """
        with self._lock:
            try:
                if self.index.ntotal == 0:
                    return []
                
                query_np = np.array([query_vector], dtype=np.float32)
                query_np = self._normalize(query_np)
                
                # Search with larger k if we need to filter
                search_k = min(top_k * 10, self.index.ntotal) if filter_metadata else top_k
                
                distances, indices = self.index.search(query_np, search_k)
                
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < 0 or idx >= len(self._metadata):
                        continue
                    
                    meta = self._metadata[idx]
                    
                    # Apply metadata filters
                    if filter_metadata:
                        match = all(
                            meta.get(k) == v for k, v in filter_metadata.items()
                        )
                        if not match:
                            continue
                    
                    results.append({
                        "id": meta.get("id"),
                        "similarity_score": float(dist),  # Inner product after normalization = cosine similarity
                        "metadata": meta,
                        "text": meta.get("text", "")
                    })
                    
                    if len(results) >= top_k:
                        break
                
                return results
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                raise
    
    def delete(
        self,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delete vectors by ID or metadata filter.
        Note: FAISS doesn't support direct deletion, so we rebuild the index.
        
        Args:
            ids: List of IDs to delete
            filter_metadata: Metadata filter to match vectors for deletion
            
        Returns:
            Dictionary with deletion result info
        """
        with self._lock:
            try:
                if ids is None and filter_metadata is None:
                    raise ValueError("Must provide either ids or filter_metadata")
                
                # Find indices to keep
                indices_to_delete = set()
                
                for i, meta in enumerate(self._metadata):
                    should_delete = False
                    
                    if ids and meta.get("id") in ids:
                        should_delete = True
                    
                    if filter_metadata:
                        match = all(
                            meta.get(k) == v for k, v in filter_metadata.items()
                        )
                        if match:
                            should_delete = True
                    
                    if should_delete:
                        indices_to_delete.add(i)
                
                if not indices_to_delete:
                    return {"status": "success", "deleted": 0}
                
                # Rebuild index without deleted vectors
                # This is expensive but necessary for FAISS
                indices_to_keep = [i for i in range(len(self._metadata)) if i not in indices_to_delete]
                
                if indices_to_keep:
                    # Extract vectors to keep
                    vectors_to_keep = np.array([
                        self.index.reconstruct(i) for i in indices_to_keep
                    ], dtype=np.float32)
                    
                    # Rebuild index
                    self._index = faiss.IndexFlatIP(self.dimension)
                    self._index.add(vectors_to_keep)
                    
                    # Update metadata
                    new_metadata = []
                    for new_idx, old_idx in enumerate(indices_to_keep):
                        meta = self._metadata[old_idx].copy()
                        meta["index"] = new_idx
                        new_metadata.append(meta)
                    self._metadata = new_metadata
                else:
                    # Delete everything
                    self._index = faiss.IndexFlatIP(self.dimension)
                    self._metadata = []
                
                self._save_index()
                
                return {
                    "status": "success",
                    "deleted": len(indices_to_delete),
                    "remaining": self.index.ntotal
                }
                
            except Exception as e:
                logger.error(f"Delete error: {e}")
                raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        return {
            "total_vectors": self.index.ntotal if self._index else 0,
            "dimension": self.dimension,
            "index_path": self.index_path
        }
    
    def clear(self):
        """Clear all vectors from the index."""
        with self._lock:
            self._index = faiss.IndexFlatIP(self.dimension)
            self._metadata = []
            self._save_index()


# Global singleton instance
_faiss_store: Optional[FAISSStore] = None


def get_faiss_store(
    dimension: int = 384,
    index_path: str = "./faiss_index"
) -> FAISSStore:
    """Get or create the FAISS store singleton."""
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FAISSStore(dimension=dimension, index_path=index_path)
    return _faiss_store
