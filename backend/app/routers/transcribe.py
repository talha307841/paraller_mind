"""
Transcription API endpoint using faster-whisper.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import base64
import numpy as np
from ..services.transcription import get_transcription_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])


# Request/Response models
class WordTimestamp(BaseModel):
    """Word-level timestamp model."""
    word: str
    start: float
    end: float
    probability: Optional[float] = None


class TranscriptSegment(BaseModel):
    """Transcript segment with timestamps."""
    id: int
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    words: List[WordTimestamp] = []


class TranscribeRequest(BaseModel):
    """Request model for transcription."""
    audio_data: str = Field(..., description="Audio data as base64 string or float32 PCM bytes")
    audio_format: str = Field(default="base64", description="Format: 'base64' or 'float32_pcm'")
    sample_rate: int = Field(default=16000, description="Sample rate of the audio")


class TranscribeResponse(BaseModel):
    """Response model for transcription."""
    text: str = Field(..., description="Full transcribed text")
    segments: List[TranscriptSegment] = Field(default=[], description="Transcript segments with timestamps")
    language: Optional[str] = Field(None, description="Detected language")
    language_probability: Optional[float] = Field(None, description="Language detection confidence")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    diarization: Optional[Dict[str, Any]] = Field(None, description="Diarization placeholder")


class DiarizationSegment(BaseModel):
    """Diarization segment placeholder."""
    speaker_id: str
    start: float
    end: float


class DiarizationResponse(BaseModel):
    """Diarization response placeholder."""
    segments: List[DiarizationSegment] = []
    num_speakers: int = 0
    message: str = "Diarization is not yet implemented. This is a placeholder."


@router.post("", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio chunks.
    
    Accepts audio in float32 PCM or base64 format and returns
    transcribed text with timestamps.
    """
    try:
        service = get_transcription_service()
        
        # Decode audio data
        if request.audio_format == "base64":
            audio_bytes = base64.b64decode(request.audio_data)
        else:
            audio_bytes = request.audio_data.encode('latin-1')
        
        result = service.transcribe_audio_bytes(
            audio_data=audio_bytes,
            audio_format="float32_pcm",  # After decoding, it's raw bytes
            sample_rate=request.sample_rate
        )
        
        # Convert to response model
        segments = [
            TranscriptSegment(
                id=seg["id"],
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                confidence=seg.get("confidence"),
                words=[WordTimestamp(**w) for w in seg.get("words", [])]
            )
            for seg in result.get("segments", [])
        ]
        
        return TranscribeResponse(
            text=result["text"],
            segments=segments,
            language=result.get("language"),
            language_probability=result.get("language_probability"),
            duration=result.get("duration"),
            diarization=result.get("diarization")
        )
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/file", response_model=TranscribeResponse)
async def transcribe_file(
    file: UploadFile = File(..., description="Audio file to transcribe")
):
    """
    Transcribe an uploaded audio file.
    
    Accepts common audio formats (wav, mp3, m4a, etc.) and returns
    transcribed text with timestamps.
    """
    try:
        import tempfile
        import os
        
        # Save uploaded file to temp location
        suffix = f".{file.filename.split('.')[-1]}" if '.' in file.filename else '.wav'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            service = get_transcription_service()
            result = service.transcribe_file(tmp_path)
            
            # Convert to response model
            segments = [
                TranscriptSegment(
                    id=seg["id"],
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                    confidence=seg.get("confidence"),
                    words=[WordTimestamp(**w) for w in seg.get("words", [])]
                )
                for seg in result.get("segments", [])
            ]
            
            return TranscribeResponse(
                text=result["text"],
                segments=segments,
                language=result.get("language"),
                language_probability=result.get("language_probability"),
                duration=result.get("duration"),
                diarization=result.get("diarization")
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
    except Exception as e:
        logger.error(f"File transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.get("/diarization", response_model=DiarizationResponse)
async def get_diarization_placeholder():
    """
    Diarization placeholder endpoint.
    
    Note: Full diarization implementation would require additional
    dependencies like pyannote.audio with HuggingFace token.
    """
    return DiarizationResponse(
        segments=[],
        num_speakers=0,
        message="Diarization is not yet implemented. This is a placeholder. "
                "For production use, integrate pyannote.audio or a similar library."
    )
