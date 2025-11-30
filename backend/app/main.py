from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import aiofiles
import uuid
from datetime import datetime

from .database import get_db, create_tables
from .models import Conversation, TranscriptSegment, ConversationStatus
from .schemas import (
    ConversationResponse, ConversationListResponse, SuggestedRepliesResponse,
    SummarizeResponse, UploadResponse
)

# Import new routers for open-source endpoints
from .routers import (
    transcribe_router,
    embeddings_router,
    memory_router,
    suggest_router,
    events_router
)

# Import open-source services
from .services.transcription import get_transcription_service
from .services.embeddings import get_embedding_service
from .services.faiss_store import get_faiss_store
from .services.ollama_client import get_ollama_client

# Create FastAPI app
app = FastAPI(
    title="Parallel Mind Audio App",
    description="Advanced conversational AI with open-source audio processing, embeddings, and semantic search. "
                "Uses faster-whisper for transcription, sentence-transformers for embeddings, FAISS for vector storage, "
                "and Ollama for LLM inference.",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()

# Include new open-source routers
app.include_router(transcribe_router)
app.include_router(embeddings_router)
app.include_router(memory_router)
app.include_router(suggest_router)
app.include_router(events_router)

@app.get("/")
async def root():
    return {"message": "Parallel Mind Audio App API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/upload", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload audio file and start processing pipeline using open-source transcription"""
    
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'wav'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("audio_files", unique_filename)
    
    # Ensure audio_files directory exists
    os.makedirs("audio_files", exist_ok=True)
    
    try:
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create conversation record
        conversation = Conversation(
            filename=unique_filename,
            status=ConversationStatus.UPLOADED
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # Process synchronously using faster-whisper (for simplicity)
        # In production, you'd want to use background tasks or Celery
        try:
            transcription_service = get_transcription_service()
            result = transcription_service.transcribe_file(file_path)
            
            # Save transcript segments
            for i, seg in enumerate(result.get("segments", [])):
                transcript_segment = TranscriptSegment(
                    conversation_id=conversation.id,
                    speaker_label=f"SPEAKER_{i % 2:02d}",  # Simple alternating speaker assignment
                    text=seg["text"],
                    start_time=seg["start"],
                    end_time=seg["end"],
                    confidence=seg.get("confidence")
                )
                db.add(transcript_segment)
            
            # Generate embeddings and store in FAISS
            embedding_service = get_embedding_service()
            faiss_store = get_faiss_store()
            
            segments_data = []
            for seg in result.get("segments", []):
                segments_data.append({
                    "text": seg["text"],
                    "conversation_id": str(conversation.id),
                    "speaker_id": f"SPEAKER_{i % 2:02d}",
                    "start_time": seg["start"],
                    "end_time": seg["end"]
                })
            
            if segments_data:
                texts = [s["text"] for s in segments_data]
                embeddings = embedding_service.embed_batch(texts)
                faiss_store.upsert(vectors=embeddings, metadata=segments_data)
            
            conversation.status = ConversationStatus.PROCESSED
            db.commit()
            
        except Exception as e:
            conversation.status = ConversationStatus.ERROR
            db.commit()
            raise
        
        return UploadResponse(
            conversation_id=conversation.id,
            message="Audio uploaded and processed successfully.",
            status="processed"
        )
        
    except Exception as e:
        # Clean up file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all conversations with pagination"""
    
    conversations = db.query(Conversation).offset(skip).limit(limit).all()
    total = db.query(Conversation).count()
    
    return ConversationListResponse(
        conversations=conversations,
        total=total
    )

@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Get conversation details and transcript"""
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@app.post("/api/conversations/{conversation_id}/suggest-reply", response_model=SuggestedRepliesResponse)
async def suggest_reply(
    conversation_id: int,
    query: str,
    db: Session = Depends(get_db)
):
    """Generate suggested replies based on conversation context using Ollama"""
    
    # Verify conversation exists and is processed
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.status != ConversationStatus.PROCESSED:
        raise HTTPException(status_code=400, detail="Conversation not yet processed")
    
    try:
        # Get relevant context from FAISS
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        
        query_embedding = embedding_service.embed(query)
        context_segments = faiss_store.search(
            query_vector=query_embedding,
            top_k=5,
            filter_metadata={"conversation_id": str(conversation_id)}
        )
        
        if not context_segments:
            raise HTTPException(status_code=404, detail="No relevant context found")
        
        # Build prompt for LLM
        context_text = "\n".join([
            f"{seg.get('metadata', {}).get('speaker_id', 'Unknown')}: {seg.get('text', '')}"
            for seg in context_segments
        ])
        
        prompt = f"""Based on the following conversation context, suggest 3 possible concise replies for the current user.

Context:
{context_text}

Query: {query}

Please provide 3 different reply suggestions that would be appropriate and contextually relevant:"""

        # Call Ollama for suggestions
        ollama_client = get_ollama_client()
        
        try:
            response = await ollama_client.generate(
                prompt=prompt,
                system="You are a helpful assistant that suggests contextually appropriate replies to conversations.",
                options={"temperature": 0.7}
            )
            suggestions_text = response.get("response", "")
        except Exception as e:
            # Fallback if Ollama is not available
            suggestions_text = "1. I understand your point.\n2. Could you elaborate on that?\n3. That's an interesting perspective."
        
        # Parse suggestions
        suggestions = []
        lines = suggestions_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                clean_line = line.lstrip('0123456789.- ').strip()
                if clean_line:
                    suggestions.append(clean_line)
        
        if not suggestions:
            suggestions = [line.strip() for line in suggestions_text.split('\n') if line.strip()]
        
        suggestions = suggestions[:3]
        
        # Format context segments for response
        formatted_segments = [
            {
                "speaker_label": seg.get("metadata", {}).get("speaker_id", "Unknown"),
                "text": seg.get("text", ""),
                "start_time": seg.get("metadata", {}).get("start_time", 0),
                "end_time": seg.get("metadata", {}).get("end_time", 0)
            }
            for seg in context_segments
        ]
        
        return SuggestedRepliesResponse(
            replies=suggestions,
            context_segments=formatted_segments
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@app.post("/api/conversations/{conversation_id}/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Generate a summary of the conversation using Ollama"""
    
    # Verify conversation exists and is processed
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.status != ConversationStatus.PROCESSED:
        raise HTTPException(status_code=400, detail="Conversation not yet processed")
    
    try:
        # Get all transcript segments
        segments = db.query(TranscriptSegment).filter(
            TranscriptSegment.conversation_id == conversation_id
        ).order_by(TranscriptSegment.start_time).all()
        
        if not segments:
            raise HTTPException(status_code=404, detail="No transcript found")
        
        # Build full transcript
        transcript = "\n".join([
            f"{seg.speaker_label}: {seg.text}"
            for seg in segments
        ])
        
        prompt = f"""Please provide a concise summary of the key points and outcomes of this conversation.

Transcript:
{transcript}

Please provide:
1. A brief summary of the main discussion points
2. Key outcomes or decisions made
3. Any action items mentioned"""

        # Call Ollama for summarization
        ollama_client = get_ollama_client()
        
        try:
            response = await ollama_client.generate(
                prompt=prompt,
                system="You are a helpful assistant that summarizes conversations concisely and identifies key points.",
                options={"temperature": 0.3}
            )
            summary_text = response.get("response", "")
        except Exception as e:
            # Fallback if Ollama is not available
            summary_text = "Unable to generate summary. Please ensure Ollama is running."
        
        # Extract key points (simple parsing)
        lines = summary_text.split('\n')
        key_points = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or (len(line) > 0 and line[0].isdigit())):
                clean_line = line.lstrip('0123456789.-• ').strip()
                if clean_line:
                    key_points.append(clean_line)
        
        return SummarizeResponse(
            summary=summary_text,
            key_points=key_points
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

@app.get("/api/conversations/{conversation_id}/status")
async def get_conversation_status(conversation_id: int, db: Session = Depends(get_db)):
    """Get the current processing status of a conversation"""
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "status": conversation.status,
        "filename": conversation.filename,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at
    }

@app.get("/api/search")
async def search_conversations(
    query: str,
    conversation_id: int = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Search for conversation segments using semantic similarity with FAISS"""
    
    try:
        embedding_service = get_embedding_service()
        faiss_store = get_faiss_store()
        
        query_embedding = embedding_service.embed(query)
        
        filter_metadata = None
        if conversation_id:
            filter_metadata = {"conversation_id": str(conversation_id)}
        
        results = faiss_store.search(
            query_vector=query_embedding,
            top_k=limit,
            filter_metadata=filter_metadata
        )
        
        # Format results
        formatted_results = [
            {
                "text": r.get("text", ""),
                "speaker_label": r.get("metadata", {}).get("speaker_id", "Unknown"),
                "start_time": r.get("metadata", {}).get("start_time", 0),
                "end_time": r.get("metadata", {}).get("end_time", 0),
                "similarity_score": r.get("similarity_score", 0),
                "conversation_id": r.get("metadata", {}).get("conversation_id")
            }
            for r in results
        ]
        
        return {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
