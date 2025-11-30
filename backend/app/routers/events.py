"""
WebSocket endpoint for real-time event streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Set
import json
import asyncio
import logging
from datetime import datetime
from ..services.faiss_store import get_faiss_store
from ..services.embeddings import get_embedding_service
from ..services.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


class ConnectionManager:
    """Manages WebSocket connections for real-time event streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client."""
        async with self._lock:
            websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        async with self._lock:
            connections = list(self.active_connections.items())
        
        for client_id, websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


async def generate_streaming_suggestion(
    text: str,
    conversation_id: Optional[str] = None,
    top_k: int = 5,
    model: str = "llama3"
) -> AsyncIterator:
    """Generate a suggestion with streaming output."""
    
    embedding_service = get_embedding_service()
    faiss_store = get_faiss_store()
    ollama_client = get_ollama_client()
    
    # Embed and search
    query_embedding = embedding_service.embed(text)
    
    filter_metadata = {}
    if conversation_id:
        filter_metadata["conversation_id"] = conversation_id
    
    search_results = faiss_store.search(
        query_vector=query_embedding,
        top_k=top_k,
        filter_metadata=filter_metadata if filter_metadata else None
    )
    
    # Build context
    context_parts = []
    for i, mem in enumerate(search_results, 1):
        text_content = mem.get("text", "")
        speaker = mem.get("metadata", {}).get("speaker_id", "Unknown")
        context_parts.append(f"[{i}] {speaker}: {text_content}")
    
    context_text = "\n".join(context_parts) if context_parts else "No context."
    
    system_prompt = """You are a helpful AI assistant providing real-time suggestions based on conversation context.
Be concise and helpful."""
    
    user_prompt = f"""Context:
{context_text}

Current input: {text}

Provide a helpful suggestion:"""
    
    # Stream response
    try:
        async for chunk in ollama_client.generate_stream(
            prompt=user_prompt,
            model=model,
            system=system_prompt,
            options={"temperature": 0.7}
        ):
            yield {
                "type": "suggestion_chunk",
                "content": chunk.get("response", ""),
                "done": chunk.get("done", False)
            }
    except Exception as e:
        yield {
            "type": "error",
            "content": str(e),
            "done": True
        }


from typing import AsyncIterator


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time suggestion streaming.
    
    Protocol:
    - Client sends JSON messages with structure:
      {
        "type": "transcribe" | "suggest" | "ping",
        "text": "...",
        "conversation_id": "...",
        "top_k": 5
      }
    
    - Server sends JSON messages with structure:
      {
        "type": "suggestion" | "suggestion_chunk" | "error" | "pong" | "connected",
        "content": "...",
        "sources": [...],
        "timestamp": "..."
      }
    """
    client_id = f"client_{id(websocket)}"
    
    await manager.connect(websocket, client_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                msg_type = data.get("type", "")
                
                if msg_type == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif msg_type == "suggest":
                    # Generate streaming suggestion
                    text = data.get("text", "")
                    conversation_id = data.get("conversation_id")
                    top_k = data.get("top_k", 5)
                    model = data.get("model", "llama3")
                    
                    if not text:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Missing 'text' field",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        continue
                    
                    # Get context first
                    embedding_service = get_embedding_service()
                    faiss_store = get_faiss_store()
                    
                    query_embedding = embedding_service.embed(text)
                    
                    filter_metadata = {}
                    if conversation_id:
                        filter_metadata["conversation_id"] = conversation_id
                    
                    search_results = faiss_store.search(
                        query_vector=query_embedding,
                        top_k=top_k,
                        filter_metadata=filter_metadata if filter_metadata else None
                    )
                    
                    # Send context
                    sources = [
                        {
                            "id": r.get("id"),
                            "text": r.get("text", ""),
                            "similarity": r.get("similarity_score", 0)
                        }
                        for r in search_results
                    ]
                    
                    await websocket.send_json({
                        "type": "context",
                        "sources": sources,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Stream suggestion
                    full_response = ""
                    async for chunk in generate_streaming_suggestion(
                        text=text,
                        conversation_id=conversation_id,
                        top_k=top_k,
                        model=model
                    ):
                        chunk["timestamp"] = datetime.utcnow().isoformat()
                        await websocket.send_json(chunk)
                        
                        if chunk["type"] == "suggestion_chunk":
                            full_response += chunk.get("content", "")
                    
                    # Send final complete message
                    await websocket.send_json({
                        "type": "suggestion_complete",
                        "content": full_response,
                        "sources": sources,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif msg_type == "transcribe_notify":
                    # Notification that new transcript is available
                    # This can trigger automatic suggestion generation
                    text = data.get("text", "")
                    conversation_id = data.get("conversation_id")
                    
                    await websocket.send_json({
                        "type": "transcribe_received",
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Unknown message type: {msg_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except json.JSONDecodeError as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Invalid JSON: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id)


@router.get("/connections")
async def get_active_connections():
    """Get the number of active WebSocket connections."""
    return {
        "active_connections": manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }
