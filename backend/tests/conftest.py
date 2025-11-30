"""Pytest configuration and fixtures for backend tests."""
import pytest
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock heavy ML dependencies before importing anything else
mock_whisper = MagicMock()
mock_sentence_transformers = MagicMock()
mock_faiss = MagicMock()
mock_ollama = MagicMock()
mock_torch = MagicMock()
mock_transformers = MagicMock()
mock_librosa = MagicMock()
mock_soundfile = MagicMock()
mock_ctranslate2 = MagicMock()
mock_celery = MagicMock()
mock_redis = MagicMock()

# Add mocks to sys.modules
sys.modules['faster_whisper'] = mock_whisper
sys.modules['sentence_transformers'] = mock_sentence_transformers
sys.modules['faiss'] = mock_faiss
sys.modules['ollama'] = mock_ollama
sys.modules['torch'] = mock_torch
sys.modules['transformers'] = mock_transformers
sys.modules['librosa'] = mock_librosa
sys.modules['soundfile'] = mock_soundfile
sys.modules['ctranslate2'] = mock_ctranslate2
sys.modules['celery'] = mock_celery
sys.modules['redis'] = mock_redis

# Now import the application
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
# Import Base from models, not database (they have separate Base)
from app.models import Base


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with a fresh database."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_conversation_data():
    """Sample data for creating a conversation."""
    return {
        "filename": "test_audio.wav",
        "status": "uploaded"
    }


@pytest.fixture
def sample_transcript_data():
    """Sample transcript segment data."""
    return {
        "speaker_label": "SPEAKER_00",
        "text": "Hello, how are you doing today?",
        "start_time": 0.0,
        "end_time": 2.5,
        "confidence": 0.95
    }
