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
from .celery_worker import diarize_and_transcribe, get_task_status
from .vector_db import vector_db

# Create FastAPI app
app = FastAPI(
    title="Parallel Mind Audio App",
    description="Advanced conversational AI with audio processing, diarization, and semantic search",
    version="1.0.0"
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
    """Upload audio file and start processing pipeline"""
    
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'wav'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("audio_files", unique_filename)
    
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
        
        # Start async processing
        task = diarize_and_transcribe.delay(conversation.id, file_path)
        
        return UploadResponse(
            conversation_id=conversation.id,
            message="Audio uploaded successfully. Processing started.",
            status="uploaded"
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
    """Generate suggested replies based on conversation context"""
    
    # Verify conversation exists and is processed
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.status != ConversationStatus.PROCESSED:
        raise HTTPException(status_code=400, detail="Conversation not yet processed")
    
    try:
        # Get relevant context from vector database
        context_segments = vector_db.search_similar_segments(conversation_id, query, limit=5)
        
        if not context_segments:
            raise HTTPException(status_code=404, detail="No relevant context found")
        
        # Build prompt for LLM
        context_text = "\n".join([
            f"{seg['speaker_label']}: {seg['text']}"
            for seg in context_segments
        ])
        
        prompt = f"""Based on the following conversation context, suggest 3 possible concise replies for the current user.

Context:
{context_text}

Query: {query}

Please provide 3 different reply suggestions that would be appropriate and contextually relevant:"""

        # Call OpenAI for suggestions
        import openai
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that suggests contextually appropriate replies to conversations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        # Parse suggestions (assuming they come as numbered list)
        suggestions_text = response.choices[0].message.content
        suggestions = []
        
        # Simple parsing - look for numbered items
        lines = suggestions_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering and clean up
                clean_line = line.lstrip('0123456789.- ').strip()
                if clean_line:
                    suggestions.append(clean_line)
        
        # If parsing failed, just split by lines
        if not suggestions:
            suggestions = [line.strip() for line in suggestions_text.split('\n') if line.strip()]
        
        # Limit to 3 suggestions
        suggestions = suggestions[:3]
        
        return SuggestedRepliesResponse(
            replies=suggestions,
            context_segments=context_segments
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@app.post("/api/conversations/{conversation_id}/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """Generate a summary of the conversation"""
    
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
        
        # Call OpenAI for summarization
        import openai
        client = openai.OpenAI()
        
        prompt = f"""Please provide a concise summary of the key points and outcomes of this conversation.

Transcript:
{transcript}

Please provide:
1. A brief summary of the main discussion points
2. Key outcomes or decisions made
3. Any action items mentioned"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely and identifies key points."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        summary_text = response.choices[0].message.content
        
        # Extract key points (simple parsing)
        lines = summary_text.split('\n')
        key_points = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                clean_line = line.lstrip('0123456789.-• ').strip()
                if clean_line:
                    key_points.append(clean_line)
        
        return SummarizeResponse(
            summary=summary_text,
            key_points=key_points
        )
        
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
    """Search for conversation segments using semantic similarity"""
    
    try:
        if conversation_id:
            # Search within specific conversation
            results = vector_db.search_similar_segments(conversation_id, query, limit)
        else:
            # Search across all conversations (would need to implement this in vector_db)
            # For now, return error
            raise HTTPException(status_code=400, detail="Global search not yet implemented. Please specify conversation_id.")
        
        return {
            "query": query,
            "results": results,
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
