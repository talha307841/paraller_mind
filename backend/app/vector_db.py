import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any
import openai
import json

class VectorDB:
    def __init__(self):
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = os.getenv("CHROMA_PORT", "8000")
        self.openai_client = openai.OpenAI()
        
        # Initialize ChromaDB client
        self.client = chromadb.HttpClient(
            host=self.chroma_host,
            port=self.chroma_port,
            settings=Settings(
                chroma_api_impl="rest",
                persist_directory="./chroma_db"
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="conversation_segments",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_conversation_segments(self, conversation_id: int, segments: List[Dict[str, Any]]) -> bool:
        """Add conversation segments with embeddings to the vector database"""
        try:
            # Prepare documents and metadata
            documents = []
            metadatas = []
            ids = []
            
            for i, segment in enumerate(segments):
                # Generate embedding for the text
                response = self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=segment["text"]
                )
                embedding = response.data[0].embedding
                
                # Create unique ID
                segment_id = f"conv_{conversation_id}_seg_{i}"
                
                documents.append(segment["text"])
                metadatas.append({
                    "conversation_id": conversation_id,
                    "speaker_label": segment["speaker_label"],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "segment_index": i
                })
                ids.append(segment_id)
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding for embedding in [response.data[0].embedding for response in [self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=segment["text"]
                ) for segment in segments]]]],
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding segments to vector DB: {e}")
            return False
    
    def search_similar_segments(self, conversation_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for segments similar to the query within a specific conversation"""
        try:
            # Generate embedding for the query
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = response.data[0].embedding
            
            # Search in the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"conversation_id": conversation_id}
            )
            
            # Format results
            segments = []
            for i in range(len(results["documents"][0])):
                segments.append({
                    "text": results["documents"][0][i],
                    "speaker_label": results["metadatas"][0][i]["speaker_label"],
                    "start_time": results["metadatas"][0][i]["start_time"],
                    "end_time": results["metadatas"][0][i]["end_time"],
                    "distance": results["distances"][0][i]
                })
            
            return segments
            
        except Exception as e:
            print(f"Error searching vector DB: {e}")
            return []
    
    def get_conversation_context(self, conversation_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent segments from a conversation for context"""
        try:
            # Get all segments for the conversation
            results = self.collection.get(
                where={"conversation_id": conversation_id}
            )
            
            # Sort by segment index and take the most recent
            segments_with_index = []
            for i, metadata in enumerate(results["metadatas"]):
                segments_with_index.append({
                    "text": results["documents"][i],
                    "speaker_label": metadata["speaker_label"],
                    "start_time": metadata["start_time"],
                    "end_time": metadata["end_time"],
                    "segment_index": metadata["segment_index"]
                })
            
            # Sort by segment index and take the most recent
            segments_with_index.sort(key=lambda x: x["segment_index"], reverse=True)
            return segments_with_index[:limit]
            
        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return []

# Global instance
vector_db = VectorDB()
