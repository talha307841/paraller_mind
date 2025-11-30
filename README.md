# 🧠 Parallel Mind - Open-Source Conversational AI

A complete, containerized full-stack application using **only open-source components** for audio processing, semantic search, and AI-powered conversation assistance. Records audio, transcribes it using faster-whisper, generates embeddings with sentence-transformers, stores vectors in FAISS, and uses Ollama with Llama3 for intelligent responses.

## 🚀 Features

- **Audio Recording**: Frontend UI to start/stop recording using MediaRecorder API
- **Local Transcription**: High-quality audio-to-text using faster-whisper (no API keys needed!)
- **Semantic Search**: Vector-based search using FAISS and sentence-transformers embeddings
- **AI Insights**: Llama3-powered summaries and suggestions via Ollama
- **Real-time Streaming**: WebSocket support for live suggestions
- **100% Open Source**: No paid API dependencies - runs completely offline
- **Modern UI**: Beautiful React frontend with Tailwind CSS

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Ollama        │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Llama3)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       
         │                       │                       
         ▼                       ▼                       
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │     FAISS       │    │  faster-whisper │
│   (Reverse      │    │  (Vector DB)    │    │  (Transcription)│
│    Proxy)       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend (100% Open Source)
- **FastAPI**: Modern, fast web framework for building APIs
- **faster-whisper**: Local speech-to-text transcription (CTranslate2)
- **sentence-transformers**: Local embeddings with "all-MiniLM-L6-v2"
- **FAISS**: Facebook AI Similarity Search for vector storage
- **Ollama**: Local LLM inference with Llama3
- **SQLAlchemy**: SQL toolkit and ORM
- **Redis**: Message broker (optional)

### Frontend
- **React 18**: Modern UI framework
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icons

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and load balancing

## 📋 Prerequisites

- Docker and Docker Compose
- At least 8GB RAM available for containers
- GPU recommended for faster transcription (but not required)
- ~10GB disk space for models

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd parallel-mind
```

### 2. Start All Services
```bash
# Start all containers (this may take a while on first run)
docker-compose up -d

# Wait for services to be ready
docker-compose logs -f backend
```

### 3. Pull the Llama3 Model
```bash
# After Ollama container is running, pull the model
docker exec -it $(docker ps -q -f name=ollama) ollama pull llama3
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Ollama**: http://localhost:11434

## 🔍 API Endpoints

### Transcription
```bash
# Transcribe audio from base64/PCM data
POST /api/transcribe
{
  "audio_data": "<base64_encoded_audio>",
  "audio_format": "base64",
  "sample_rate": 16000
}

# Transcribe audio file
POST /api/transcribe/file
# (multipart/form-data with audio file)
```

### Embeddings
```bash
# Generate embedding for text
POST /api/embeddings
{
  "text": "Your text here"
}

# Batch embeddings
POST /api/embeddings/batch
{
  "texts": ["Text 1", "Text 2", "Text 3"]
}

# Calculate similarity
POST /api/embeddings/similarity
{
  "text1": "First text",
  "text2": "Second text"
}
```

### Memory (FAISS Vector Store)
```bash
# Upsert transcript chunks
POST /api/memory/upsert
{
  "chunks": [
    {
      "text": "Hello, how are you?",
      "conversation_id": "conv_123",
      "speaker_id": "speaker_1",
      "timestamp": "2024-01-01T10:00:00Z"
    }
  ]
}

# Search memories
POST /api/memory/search
{
  "query": "greeting",
  "top_k": 5,
  "conversation_id": "conv_123"
}

# Get memory stats
GET /api/memory/stats

# Clear all memories
POST /api/memory/clear
```

### Suggestions (RAG with Ollama)
```bash
# Generate suggestion based on context
POST /api/suggest
{
  "text": "What should I reply about the project deadline?",
  "conversation_id": "conv_123",
  "top_k": 5,
  "model": "llama3"
}

# Get detailed suggestion with RAG context
POST /api/suggest/detailed
{
  "text": "What should I reply?",
  "top_k": 5
}

# Check suggestion health
GET /api/suggest/health
```

### Real-time Events (WebSocket)
```bash
# Connect to WebSocket
wscat -c ws://localhost:8001/api/events/stream

# Send suggestion request
{"type": "suggest", "text": "Hello", "conversation_id": "123"}

# Ping/pong
{"type": "ping"}
```

### Legacy Endpoints
```bash
# Upload audio file
POST /api/upload

# List conversations
GET /api/conversations

# Get conversation
GET /api/conversations/{id}

# Get conversation status
GET /api/conversations/{id}/status

# Summarize conversation
POST /api/conversations/{id}/summarize

# Suggest reply
POST /api/conversations/{id}/suggest-reply?query=...

# Search
GET /api/search?query=...&conversation_id=...

# Health check
GET /health
```

## 📝 Testing the API with curl

### Test Embeddings
```bash
# Generate an embedding
curl -X POST "http://localhost:8001/api/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you today?"}'

# Response:
# {"embedding": [0.123, -0.456, ...], "dimension": 384, "model": "all-MiniLM-L6-v2"}
```

### Test Memory Storage
```bash
# Store some memories
curl -X POST "http://localhost:8001/api/memory/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "chunks": [
      {"text": "The project deadline is next Friday.", "conversation_id": "test", "speaker_id": "Alice"},
      {"text": "We need to finish the documentation first.", "conversation_id": "test", "speaker_id": "Bob"},
      {"text": "I will handle the testing.", "conversation_id": "test", "speaker_id": "Alice"}
    ]
  }'

# Search memories
curl -X POST "http://localhost:8001/api/memory/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "when is the deadline?", "top_k": 3}'
```

### Test Suggestions (requires Ollama running)
```bash
# Generate a suggestion
curl -X POST "http://localhost:8001/api/suggest" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the project deadline?",
    "top_k": 3
  }'
```

### Test Transcription
```bash
# Transcribe an audio file
curl -X POST "http://localhost:8001/api/transcribe/file" \
  -F "file=@your_audio.wav"
```

## 🔧 Development

### Running Locally (without Docker)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3

# 2. Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 3. Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Setup frontend (in another terminal)
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
cd backend
pytest tests/ -v
```

### Building Containers
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f ollama
```

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8001 | FastAPI application |
| ollama | 11434 | Llama3 LLM server |
| frontend | 3000 | React application |
| redis | 6379 | Message broker (optional) |
| nginx | 80 | Reverse proxy |

## 🚨 Troubleshooting

### Ollama Not Responding
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull model if not present
docker exec -it $(docker ps -q -f name=ollama) ollama pull llama3

# Check logs
docker-compose logs ollama
```

### Slow Transcription
- First transcription downloads the model (~150MB for base)
- GPU acceleration: Ensure CUDA is available
- Use smaller model: Set `WHISPER_MODEL=tiny` in environment

### Memory Issues
```bash
# Check container memory usage
docker stats

# Reduce model size if needed
# In docker-compose.yml, add:
# environment:
#   - WHISPER_MODEL=tiny  # instead of base
```

### FAISS Index Issues
```bash
# Clear the index
curl -X POST "http://localhost:8001/api/memory/clear"

# Check stats
curl "http://localhost:8001/api/memory/stats"
```

## 📊 Resource Requirements

| Component | Minimum RAM | Recommended RAM |
|-----------|-------------|-----------------|
| Backend + faster-whisper | 2GB | 4GB |
| Ollama + Llama3 | 4GB | 8GB |
| FAISS | 512MB | 1GB |
| Total | 6GB | 12GB+ |

## 🔒 Security Considerations

- **No API Keys**: This solution runs entirely locally
- **CORS**: Configure for production
- **Authentication**: Add auth for production use
- **HTTPS**: Use HTTPS in production

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast Whisper transcription
- [sentence-transformers](https://www.sbert.net/) - State-of-the-art embeddings
- [FAISS](https://github.com/facebookresearch/faiss) - Efficient similarity search
- [Ollama](https://ollama.ai/) - Run LLMs locally
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

---

**Note**: First run may take longer as models are downloaded. Ensure stable internet connection for initial setup.
