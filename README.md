# 🧠 Parallel Mind - Advanced Conversational AI

A complete, containerized full-stack application that records audio, diarizes it, transcribes it, generates embeddings for semantic search, maintains conversation history, and uses OpenAI's LLM to provide summaries and suggest context-aware replies.

## 🚀 Features

- **Audio Recording**: Frontend UI to start/stop recording using MediaRecorder API
- **Speaker Diarization**: Advanced AI-powered speaker identification using PyAnnote
- **Transcription**: High-quality audio-to-text conversion using OpenAI Whisper
- **Semantic Search**: Vector-based search using ChromaDB and OpenAI embeddings
- **AI Insights**: LLM-powered conversation summaries and suggested replies
- **Real-time Processing**: Asynchronous audio processing pipeline with Celery
- **Modern UI**: Beautiful React frontend with Tailwind CSS

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Celery        │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Worker        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   ChromaDB      │    │     Redis       │
│   (Reverse      │    │  (Vector DB)    │    │  (Message      │
│    Proxy)       │    │                 │    │   Broker)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **Celery**: Distributed task queue for async processing
- **Redis**: Message broker and caching
- **ChromaDB**: Vector database for embeddings

### AI Services
- **OpenAI API**: Whisper transcription, GPT models, embeddings
- **PyAnnote**: Speaker diarization (requires Hugging Face token)

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
- OpenAI API key
- Hugging Face token (for PyAnnote)
- At least 4GB RAM available for containers

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd parallel-mind-audio-app
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Hugging Face Configuration (for PyAnnote diarization)
HF_TOKEN=your_huggingface_token_here

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# ChromaDB Configuration
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# Database Configuration
DATABASE_URL=sqlite:///./parallel_mind.db

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend Configuration
VITE_API_BASE_URL=http://localhost:8001

# Logging Configuration
LOG_LEVEL=INFO

# Security Configuration
CORS_ORIGINS=*
```

### 3. Start the Application
```bash
docker-compose up -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **ChromaDB**: http://localhost:8000
- **Nginx**: http://localhost:80

## 🔧 Configuration

### API Keys Setup

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account and get your API key
3. Add it to your `.env` file

#### Hugging Face Token
1. Visit [Hugging Face](https://huggingface.co/)
2. Create an account and go to Settings > Access Tokens
3. Create a new token with read access
4. Add it to your `.env` file

### Alternative AI Services

If you prefer not to use PyAnnote (which requires GPU for optimal performance), you can use:

- **AssemblyAI**: Professional diarization and transcription service
- **Deepgram**: High-quality speech recognition API

## 📱 Usage

### 1. Record a Conversation
1. Navigate to the home page
2. Click the microphone button to start recording
3. Speak clearly into your microphone
4. Click the stop button when finished
5. Click upload to process the audio

### 2. View Processing Status
- Monitor the status of your conversation
- Processing includes: diarization → transcription → embedding generation
- This may take several minutes for longer recordings

### 3. Explore AI Insights
Once processing is complete:
- **View Transcript**: See the full conversation with speaker labels
- **Generate Summary**: Get AI-powered conversation summary
- **Get Suggested Replies**: Receive context-aware response suggestions
- **Semantic Search**: Find specific topics within conversations

### 4. Manage History
- View all recorded conversations
- Search through conversation history
- Access detailed views of each conversation

## 🔍 API Endpoints

### Audio Processing
- `POST /api/upload` - Upload audio file and start processing

### Conversations
- `GET /api/conversations` - List all conversations
- `GET /api/conversations/{id}` - Get conversation details
- `GET /api/conversations/{id}/status` - Get processing status

### AI Features
- `POST /api/conversations/{id}/summarize` - Generate conversation summary
- `POST /api/conversations/{id}/suggest-reply` - Get suggested replies
- `GET /api/search` - Semantic search within conversations

### Health
- `GET /health` - Health check endpoint

## 🐳 Docker Services

### Backend Service
- **Port**: 8001 (mapped from container 8000)
- **Purpose**: FastAPI application with all endpoints
- **Dependencies**: Redis, ChromaDB

### Worker Service
- **Purpose**: Celery worker for async audio processing
- **Tasks**: Diarization, transcription, embedding generation
- **Dependencies**: Redis, ChromaDB

### Frontend Service
- **Port**: 3000 (mapped from container 80)
- **Purpose**: React application served by Nginx
- **Dependencies**: Backend API

### ChromaDB Service
- **Port**: 8000
- **Purpose**: Vector database for embeddings
- **Persistence**: Docker volume

### Redis Service
- **Port**: 6379
- **Purpose**: Message broker for Celery
- **Persistence**: Docker volume

### Nginx Service
- **Port**: 80
- **Purpose**: Reverse proxy and load balancing
- **Features**: Rate limiting, gzip compression

## 🔧 Development

### Running in Development Mode
```bash
# Backend development
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development
cd frontend
npm install
npm run dev

# Celery worker
cd backend
celery -A app.celery_worker worker --loglevel=info
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
docker-compose logs -f worker
```

## 🚨 Troubleshooting

### Common Issues

#### Audio Recording Not Working
- Ensure microphone permissions are granted in the browser
- Check if HTTPS is required (some browsers require secure context)
- Verify audio device is working in system settings

#### Processing Fails
- Check OpenAI API key is valid and has credits
- Verify Hugging Face token has proper permissions
- Check container logs for specific error messages
- Ensure sufficient system resources (RAM/CPU)

#### ChromaDB Connection Issues
- Verify ChromaDB container is running: `docker-compose ps`
- Check ChromaDB logs: `docker-compose logs chromadb`
- Ensure proper network connectivity between services

#### Redis Connection Issues
- Verify Redis container is running: `docker-compose ps`
- Check Redis logs: `docker-compose logs redis`
- Ensure Redis URL is correct in environment variables

### Performance Optimization

#### For Production Use
- Use GPU-enabled containers for PyAnnote
- Implement Redis clustering for high availability
- Use external ChromaDB instance for persistence
- Implement proper monitoring and logging
- Add rate limiting and authentication

#### Resource Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores
- **GPU**: Optional but recommended for PyAnnote

## 📊 Monitoring

### Health Checks
- Backend health: `GET /health`
- Container status: `docker-compose ps`
- Service logs: `docker-compose logs [service]`

### Metrics to Monitor
- Audio processing queue length
- Processing time per conversation
- API response times
- Container resource usage
- Error rates

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **CORS**: Configure CORS origins for production
- **Rate Limiting**: Implement proper rate limiting
- **Authentication**: Add user authentication for production use
- **HTTPS**: Use HTTPS in production environments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for Whisper and GPT models
- PyAnnote team for speaker diarization
- ChromaDB for vector database
- FastAPI and React communities

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs
3. Open an issue on GitHub
4. Check the documentation

---

**Note**: This is a complex application with multiple AI services. Processing times and accuracy depend on audio quality, conversation length, and available computational resources.
