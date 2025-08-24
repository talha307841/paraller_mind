#!/bin/bash

echo "🧠 Starting Parallel Mind - Advanced Conversational AI"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy env.template to .env and configure your API keys:"
    echo "   cp env.template .env"
    echo "   # Then edit .env with your OpenAI API key and HF token"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "🚀 Please start Docker and try again"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found!"
    echo "📦 Please install Docker Compose and try again"
    exit 1
fi

echo "✅ Environment check passed"
echo "🔧 Building and starting services..."

# Build and start services
docker-compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Parallel Mind is starting up!"
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8001"
echo "   ChromaDB: http://localhost:8000"
echo ""
echo "📝 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker-compose down"
echo ""
echo "🚀 Happy conversing with AI!"
