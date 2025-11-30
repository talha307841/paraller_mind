from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import ConversationStatus

# Base schemas
class TranscriptSegmentBase(BaseModel):
    speaker_label: str
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None

class TranscriptSegmentCreate(TranscriptSegmentBase):
    pass

class TranscriptSegmentResponse(TranscriptSegmentBase):
    id: int
    conversation_id: int
    
    class Config:
        from_attributes = True

# Conversation schemas
class ConversationBase(BaseModel):
    filename: str

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    status: ConversationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    segments: List[TranscriptSegmentResponse] = []
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int

# Context segment for FAISS results
class ContextSegment(BaseModel):
    speaker_label: str
    text: str
    start_time: float
    end_time: float

# API Response schemas
class SuggestedRepliesResponse(BaseModel):
    replies: List[str]
    context_segments: List[ContextSegment]

class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str]

class UploadResponse(BaseModel):
    conversation_id: int
    message: str
    status: str

# Error schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
