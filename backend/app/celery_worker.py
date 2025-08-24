from celery import Celery
import os
import openai
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import torch
import soundfile as sf
import numpy as np
from typing import List, Dict, Any
import json
from .database import SessionLocal
from .models import Conversation, TranscriptSegment, ConversationStatus
from .vector_db import vector_db

# Initialize Celery
celery_app = Celery(
    'parallel_mind_worker',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Initialize OpenAI client
openai_client = openai.OpenAI()

# Initialize PyAnnote pipeline (requires HF token)
HF_TOKEN = os.getenv('HF_TOKEN')
if HF_TOKEN:
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HF_TOKEN
    )
    pipeline.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
else:
    pipeline = None

@celery_app.task(bind=True)
def diarize_and_transcribe(self, conversation_id: int, audio_file_path: str):
    """Main task to diarize and transcribe audio"""
    try:
        # Update conversation status to processing
        db = SessionLocal()
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise Exception(f"Conversation {conversation_id} not found")
        
        conversation.status = ConversationStatus.PROCESSING
        db.commit()
        
        # Load audio file
        audio, sample_rate = sf.read(audio_file_path)
        
        # Step 1: Speaker Diarization
        if pipeline:
            # Use PyAnnote for diarization
            diarization = pipeline(audio_file_path)
            
            # Extract speaker segments
            speaker_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker
                })
        else:
            # Fallback: use simple segmentation if PyAnnote not available
            # This is a simplified approach - in production you'd want a proper diarization service
            duration = len(audio) / sample_rate
            segment_duration = 10.0  # 10 second segments
            speaker_segments = []
            
            for i in range(0, int(duration), int(segment_duration)):
                speaker_segments.append({
                    'start': float(i),
                    'end': min(float(i + segment_duration), duration),
                    'speaker': f'SPEAKER_{i//int(segment_duration):02d}'
                })
        
        # Step 2: Transcribe each segment
        transcript_segments = []
        
        for segment in speaker_segments:
            # Extract audio segment
            start_sample = int(segment['start'] * sample_rate)
            end_sample = int(segment['end'] * sample_rate)
            segment_audio = audio[start_sample:end_sample]
            
            # Save temporary segment file
            temp_segment_path = f"/tmp/segment_{conversation_id}_{segment['start']}.wav"
            sf.write(temp_segment_path, segment_audio, sample_rate)
            
            try:
                # Transcribe with OpenAI Whisper
                with open(temp_segment_path, "rb") as audio_file:
                    transcript_response = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                
                # Create transcript segment
                transcript_segment = TranscriptSegment(
                    conversation_id=conversation_id,
                    speaker_label=segment['speaker'],
                    text=transcript_response.text,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    confidence=transcript_response.language_prob if hasattr(transcript_response, 'language_prob') else None
                )
                
                transcript_segments.append(transcript_segment)
                
                # Clean up temp file
                os.remove(temp_segment_path)
                
            except Exception as e:
                print(f"Error transcribing segment {segment}: {e}")
                continue
        
        # Save transcript segments to database
        for segment in transcript_segments:
            db.add(segment)
        db.commit()
        
        # Step 3: Generate embeddings (chain to next task)
        generate_embeddings.delay(conversation_id)
        
        return {
            'status': 'success',
            'conversation_id': conversation_id,
            'segments_processed': len(transcript_segments)
        }
        
    except Exception as e:
        # Update conversation status to error
        if 'conversation' in locals():
            conversation.status = ConversationStatus.ERROR
            db.commit()
        
        print(f"Error in diarize_and_transcribe: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        if 'db' in locals():
            db.close()

@celery_app.task(bind=True)
def generate_embeddings(self, conversation_id: int):
    """Generate embeddings for transcript segments and store in vector database"""
    try:
        db = SessionLocal()
        
        # Get conversation and segments
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise Exception(f"Conversation {conversation_id} not found")
        
        segments = db.query(TranscriptSegment).filter(TranscriptSegment.conversation_id == conversation_id).all()
        
        if not segments:
            raise Exception(f"No transcript segments found for conversation {conversation_id}")
        
        # Prepare segments for vector database
        segments_data = []
        for segment in segments:
            segments_data.append({
                'text': segment.text,
                'speaker_label': segment.speaker_label,
                'start_time': segment.start_time,
                'end_time': segment.end_time
            })
        
        # Add to vector database
        success = vector_db.add_conversation_segments(conversation_id, segments_data)
        
        if success:
            # Update conversation status to processed
            conversation.status = ConversationStatus.PROCESSED
            db.commit()
            
            return {
                'status': 'success',
                'conversation_id': conversation_id,
                'embeddings_generated': len(segments)
            }
        else:
            raise Exception("Failed to add segments to vector database")
            
    except Exception as e:
        print(f"Error in generate_embeddings: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        if 'db' in locals():
            db.close()

# Task status monitoring
@celery_app.task
def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    result = celery_app.AsyncResult(task_id)
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None
    }
