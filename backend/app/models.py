from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class ConversationStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.UPLOADED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    segments = relationship("TranscriptSegment", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, filename='{self.filename}', status='{self.status}')>"

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    speaker_label = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="segments")
    
    def __repr__(self):
        return f"<TranscriptSegment(id={self.id}, speaker='{self.speaker_label}', text='{self.text[:50]}...')>"
