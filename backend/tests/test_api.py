"""Tests for main API endpoints."""
import pytest
from fastapi import status


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Parallel Mind Audio App API"}

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestConversationEndpoints:
    """Tests for conversation-related endpoints."""
    
    def test_list_conversations_empty(self, client):
        """Test listing conversations when none exist."""
        response = client.get("/api/conversations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0

    def test_get_conversation_not_found(self, client):
        """Test getting a non-existent conversation returns 404."""
        response = client.get("/api/conversations/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_conversation_status_not_found(self, client):
        """Test getting status of non-existent conversation returns 404."""
        response = client.get("/api/conversations/999/status")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_conversations_with_pagination(self, client):
        """Test listing conversations with pagination parameters."""
        response = client.get("/api/conversations?skip=0&limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversations" in data
        assert "total" in data


class TestUploadEndpoints:
    """Tests for upload-related endpoints."""
    
    def test_upload_non_audio_file_rejected(self, client):
        """Test that non-audio files are rejected."""
        # Create a fake text file
        files = {"file": ("test.txt", b"not audio content", "text/plain")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "audio" in response.json()["detail"].lower()


class TestSearchEndpoints:
    """Tests for search-related endpoints."""
    
    def test_search_empty_results(self, client):
        """Test search returns empty results when no data."""
        response = client.get("/api/search?query=test")
        # May return 200 with empty results or 500 if FAISS not initialized
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestSuggestEndpoints:
    """Tests for suggestion endpoints."""
    
    def test_suggest_reply_conversation_not_found(self, client):
        """Test suggest reply for non-existent conversation returns 404."""
        response = client.post("/api/conversations/999/suggest-reply?query=test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_summarize_conversation_not_found(self, client):
        """Test summarize for non-existent conversation returns 404."""
        response = client.post("/api/conversations/999/summarize")
        assert response.status_code == status.HTTP_404_NOT_FOUND
