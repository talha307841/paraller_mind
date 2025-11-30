"""Tests for schema validation."""
import pytest
from pydantic import ValidationError
import sys
from unittest.mock import MagicMock

# Mock heavy ML dependencies before importing
if 'faster_whisper' not in sys.modules:
    sys.modules['faster_whisper'] = MagicMock()
    sys.modules['sentence_transformers'] = MagicMock()
    sys.modules['faiss'] = MagicMock()
    sys.modules['ollama'] = MagicMock()
    sys.modules['torch'] = MagicMock()
    sys.modules['transformers'] = MagicMock()
    sys.modules['librosa'] = MagicMock()
    sys.modules['soundfile'] = MagicMock()
    sys.modules['ctranslate2'] = MagicMock()
    sys.modules['celery'] = MagicMock()
    sys.modules['redis'] = MagicMock()

from app.routers.transcribe import TranscribeRequest, TranscribeResponse, TranscriptSegment
from app.routers.embeddings import EmbeddingRequest, EmbeddingResponse
from app.routers.memory import UpsertRequest, SearchRequest, MemoryMetadata
from app.routers.suggest import SuggestRequest


class TestTranscribeSchemas:
    """Tests for transcription-related schemas."""
    
    def test_transcribe_request_valid(self):
        """Test valid transcribe request."""
        request = TranscribeRequest(
            audio_data="base64encodeddata",
            audio_format="base64",
            sample_rate=16000
        )
        assert request.audio_data == "base64encodeddata"
        assert request.audio_format == "base64"
        assert request.sample_rate == 16000

    def test_transcribe_request_defaults(self):
        """Test transcribe request with default values."""
        request = TranscribeRequest(audio_data="data")
        assert request.audio_format == "base64"
        assert request.sample_rate == 16000


class TestEmbeddingSchemas:
    """Tests for embedding-related schemas."""
    
    def test_embedding_request_valid(self):
        """Test valid embedding request."""
        request = EmbeddingRequest(text="Hello world")
        assert request.text == "Hello world"

    def test_embedding_response_structure(self):
        """Test embedding response structure."""
        response = EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3],
            dimension=3,
            model="test-model"
        )
        assert len(response.embedding) == 3
        assert response.dimension == 3
        assert response.model == "test-model"


class TestMemorySchemas:
    """Tests for memory-related schemas."""
    
    def test_memory_upsert_request_valid(self):
        """Test valid memory upsert request."""
        chunk = MemoryMetadata(
            text="Hello world",
            conversation_id="conv_1",
            speaker_id="speaker_1"
        )
        request = UpsertRequest(chunks=[chunk])
        assert len(request.chunks) == 1
        assert request.chunks[0].text == "Hello world"

    def test_memory_search_request_valid(self):
        """Test valid memory search request."""
        request = SearchRequest(
            query="test query",
            top_k=5
        )
        assert request.query == "test query"
        assert request.top_k == 5

    def test_memory_search_request_defaults(self):
        """Test memory search request with defaults."""
        request = SearchRequest(query="test")
        assert request.top_k == 5


class TestSuggestSchemas:
    """Tests for suggestion-related schemas."""
    
    def test_suggest_request_valid(self):
        """Test valid suggest request."""
        request = SuggestRequest(
            text="What should I reply?",
            conversation_id="conv_1",
            top_k=5,
            model="llama3"
        )
        assert request.text == "What should I reply?"
        assert request.conversation_id == "conv_1"
        assert request.top_k == 5
        assert request.model == "llama3"

    def test_suggest_request_defaults(self):
        """Test suggest request with default values."""
        request = SuggestRequest(text="Hello")
        assert request.top_k == 5
        assert request.model is None
        assert request.conversation_id is None
