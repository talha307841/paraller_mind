"""
Transcription service using faster-whisper for open-source speech-to-text.
"""
import os
import base64
import tempfile
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from faster_whisper import WhisperModel
import logging

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio using faster-whisper."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
        """
        self.model_size = model_size
        self._model: Optional[WhisperModel] = None
    
    @property
    def model(self) -> WhisperModel:
        """Lazy load the Whisper model."""
        if self._model is None:
            logger.info(f"Loading faster-whisper model: {self.model_size}")
            # Use CPU compute type for compatibility
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            logger.info("faster-whisper model loaded successfully")
        return self._model
    
    def transcribe_audio_bytes(
        self,
        audio_data: bytes,
        audio_format: str = "float32_pcm",
        sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        Transcribe audio from raw bytes.
        
        Args:
            audio_data: Raw audio bytes (float32 PCM or base64 encoded)
            audio_format: Format of audio data ("float32_pcm" or "base64")
            sample_rate: Sample rate of the audio
            
        Returns:
            Dictionary containing transcription text, segments with timestamps
        """
        try:
            # Decode audio data based on format
            if audio_format == "base64":
                audio_data = base64.b64decode(audio_data)
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            elif audio_format == "float32_pcm":
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                raise ValueError(f"Unsupported audio format: {audio_format}")
            
            # Ensure audio is in correct shape
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)  # Convert to mono
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_array,
                beam_size=5,
                language=None,  # Auto-detect
                vad_filter=True,
                word_timestamps=True
            )
            
            # Process segments
            result_segments = []
            full_text = ""
            
            for segment in segments:
                segment_data = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob if hasattr(segment, 'avg_logprob') else None,
                    "words": []
                }
                
                # Add word-level timestamps if available
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        segment_data["words"].append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        })
                
                result_segments.append(segment_data)
                full_text += segment.text
            
            return {
                "text": full_text.strip(),
                "segments": result_segments,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "diarization": None  # Placeholder for diarization
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio from a file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription text, segments with timestamps
        """
        try:
            segments, info = self.model.transcribe(
                file_path,
                beam_size=5,
                language=None,
                vad_filter=True,
                word_timestamps=True
            )
            
            result_segments = []
            full_text = ""
            
            for segment in segments:
                segment_data = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob if hasattr(segment, 'avg_logprob') else None,
                    "words": []
                }
                
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        segment_data["words"].append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        })
                
                result_segments.append(segment_data)
                full_text += segment.text
            
            return {
                "text": full_text.strip(),
                "segments": result_segments,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "diarization": None
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    def transcribe_numpy_array(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        Transcribe audio from a numpy array.
        
        Args:
            audio_array: Numpy array of audio samples (float32)
            sample_rate: Sample rate of the audio
            
        Returns:
            Dictionary containing transcription text, segments with timestamps
        """
        try:
            # Ensure float32
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
            
            segments, info = self.model.transcribe(
                audio_array,
                beam_size=5,
                language=None,
                vad_filter=True,
                word_timestamps=True
            )
            
            result_segments = []
            full_text = ""
            
            for segment in segments:
                segment_data = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob if hasattr(segment, 'avg_logprob') else None,
                    "words": []
                }
                
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        segment_data["words"].append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        })
                
                result_segments.append(segment_data)
                full_text += segment.text
            
            return {
                "text": full_text.strip(),
                "segments": result_segments,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "diarization": None
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise


# Global singleton instance
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service(model_size: str = "base") -> TranscriptionService:
    """Get or create the transcription service singleton."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService(model_size=model_size)
    return _transcription_service
