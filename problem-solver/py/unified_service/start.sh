#!/bin/bash

# Start script for Unified Service
# Usage: ./start.sh [development|production]

set -e

MODE=${1:-development}

echo "=================================="
echo "OSTIS ANN Unified Service Starter"
echo "Mode: $MODE"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is running
echo -e "\n${YELLOW}[1/5]${NC} Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama is running"
else
    echo -e "${RED}✗${NC} Ollama is not running!"
    echo "Please start Ollama first:"
    echo "  ollama serve"
    exit 1
fi

# Check if TinyLlama is available
echo -e "\n${YELLOW}[2/5]${NC} Checking TinyLlama model..."
if ollama list | grep -q tinyllama; then
    echo -e "${GREEN}✓${NC} TinyLlama is available"
else
    echo -e "${RED}✗${NC} TinyLlama model not found!"
    echo "Downloading TinyLlama..."
    ollama pull tinyllama
fi

# Create necessary directories
echo -e "\n${YELLOW}[3/5]${NC} Creating directories..."
mkdir -p chroma_db temp_uploads
echo -e "${GREEN}✓${NC} Directories created"

# Check if .env exists
echo -e "\n${YELLOW}[4/5]${NC} Checking environment..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠${NC} .env file not found, creating from example..."
    cp env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Start the service
echo -e "\n${YELLOW}[5/5]${NC} Starting service..."

if [ "$MODE" == "production" ]; then
    echo "Starting in production mode..."
    uvicorn main:app --host 0.0.0.0 --port 8000
elif [ "$MODE" == "docker" ]; then
    echo "Starting with Docker..."
    cd ../../..
    docker-compose up -d unified-api
    echo -e "${GREEN}✓${NC} Service started in Docker"
    echo ""
    echo "View logs: docker logs -f ostis-ann-unified-api"
    echo "Stop service: docker-compose stop unified-api"
else
    echo "Starting in development mode..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

