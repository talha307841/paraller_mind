"""Tests for database models."""
import pytest
from datetime import datetime
from app.models import Conversation, TranscriptSegment, ConversationStatus


class TestConversationModel:
    """Tests for the Conversation model."""
    
    def test_create_conversation(self, test_db):
        """Test creating a conversation record."""
        conversation = Conversation(
            filename="test_audio.wav",
            status=ConversationStatus.UPLOADED
        )
        test_db.add(conversation)
        test_db.commit()
        test_db.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.filename == "test_audio.wav"
        assert conversation.status == ConversationStatus.UPLOADED
        assert conversation.created_at is not None

    def test_conversation_status_transitions(self, test_db):
        """Test conversation status can be updated."""
        conversation = Conversation(
            filename="test_audio.wav",
            status=ConversationStatus.UPLOADED
        )
        test_db.add(conversation)
        test_db.commit()
        
        # Update to processing
        conversation.status = ConversationStatus.PROCESSING
        test_db.commit()
        test_db.refresh(conversation)
        assert conversation.status == ConversationStatus.PROCESSING
        
        # Update to processed
        conversation.status = ConversationStatus.PROCESSED
        test_db.commit()
        test_db.refresh(conversation)
        assert conversation.status == ConversationStatus.PROCESSED

    def test_conversation_with_segments(self, test_db):
        """Test conversation with transcript segments."""
        conversation = Conversation(
            filename="test_audio.wav",
            status=ConversationStatus.PROCESSED
        )
        test_db.add(conversation)
        test_db.commit()
        test_db.refresh(conversation)
        
        # Add segments
        segment1 = TranscriptSegment(
            conversation_id=conversation.id,
            speaker_label="SPEAKER_00",
            text="Hello, how are you?",
            start_time=0.0,
            end_time=2.0,
            confidence=0.95
        )
        segment2 = TranscriptSegment(
            conversation_id=conversation.id,
            speaker_label="SPEAKER_01",
            text="I am doing great!",
            start_time=2.0,
            end_time=4.0,
            confidence=0.92
        )
        test_db.add(segment1)
        test_db.add(segment2)
        test_db.commit()
        
        # Verify relationship
        test_db.refresh(conversation)
        assert len(conversation.segments) == 2


class TestTranscriptSegmentModel:
    """Tests for the TranscriptSegment model."""
    
    def test_create_transcript_segment(self, test_db):
        """Test creating a transcript segment."""
        # First create a conversation
        conversation = Conversation(
            filename="test_audio.wav",
            status=ConversationStatus.PROCESSED
        )
        test_db.add(conversation)
        test_db.commit()
        test_db.refresh(conversation)
        
        # Create segment
        segment = TranscriptSegment(
            conversation_id=conversation.id,
            speaker_label="SPEAKER_00",
            text="Test transcript text",
            start_time=0.0,
            end_time=2.5,
            confidence=0.95
        )
        test_db.add(segment)
        test_db.commit()
        test_db.refresh(segment)
        
        assert segment.id is not None
        assert segment.conversation_id == conversation.id
        assert segment.speaker_label == "SPEAKER_00"
        assert segment.text == "Test transcript text"
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5
        assert segment.confidence == 0.95

    def test_segment_without_confidence(self, test_db):
        """Test segment can be created without confidence score."""
        conversation = Conversation(
            filename="test_audio.wav",
            status=ConversationStatus.PROCESSED
        )
        test_db.add(conversation)
        test_db.commit()
        test_db.refresh(conversation)
        
        segment = TranscriptSegment(
            conversation_id=conversation.id,
            speaker_label="SPEAKER_00",
            text="Test text",
            start_time=0.0,
            end_time=1.0
        )
        test_db.add(segment)
        test_db.commit()
        test_db.refresh(segment)
        
        assert segment.confidence is None


class TestConversationStatus:
    """Tests for the ConversationStatus enum."""
    
    def test_status_values(self):
        """Test all status values are defined."""
        assert ConversationStatus.UPLOADED.value == "uploaded"
        assert ConversationStatus.PROCESSING.value == "processing"
        assert ConversationStatus.PROCESSED.value == "processed"
        assert ConversationStatus.ERROR.value == "error"
