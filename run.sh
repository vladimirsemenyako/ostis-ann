#!/bin/bash

# OSTIS ANN Unified Service Local Runner
# Allows running the service locally without Docker

# Don't exit on error for background processes
set +e

# Save script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_MODEL="tinyllama"
DEFAULT_API_PORT=8000
DEFAULT_FRONTEND_PORT=8080
DEFAULT_OLLAMA_URL="http://localhost:11434"

# Parse command line arguments
MODEL="${1:-$DEFAULT_MODEL}"
API_PORT="${2:-$DEFAULT_API_PORT}"
FRONTEND_PORT="${3:-$DEFAULT_FRONTEND_PORT}"
OLLAMA_URL="${4:-$DEFAULT_OLLAMA_URL}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}OSTIS ANN Unified Service${NC}"
echo -e "${BLUE}Local Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Model: ${YELLOW}${MODEL}${NC}"
echo -e "  API Port: ${YELLOW}${API_PORT}${NC}"
echo -e "  Frontend Port: ${YELLOW}${FRONTEND_PORT}${NC}"
echo -e "  Ollama URL: ${YELLOW}${OLLAMA_URL}${NC}"
echo ""

# Check if Ollama is running
echo -e "${BLUE}Checking Ollama connection...${NC}"
if ! curl -s "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to Ollama at ${OLLAMA_URL}${NC}"
    echo -e "${YELLOW}Please make sure Ollama is running:${NC}"
    echo -e "  ollama serve"
    exit 1
fi

# Check if model is available
echo -e "${BLUE}Checking if model '${MODEL}' is available...${NC}"
if ! curl -s "${OLLAMA_URL}/api/tags" | grep -q "\"name\":\"${MODEL}\""; then
    echo -e "${YELLOW}Warning: Model '${MODEL}' not found in Ollama${NC}"
    echo -e "${YELLOW}Available models:${NC}"
    curl -s "${OLLAMA_URL}/api/tags" | grep -o '"name":"[^"]*"' | sed 's/"name":"//;s/"//' | head -5
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python
echo -e "${BLUE}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}Found: ${PYTHON_VERSION}${NC}"

# Check Node.js
echo -e "${BLUE}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: node not found${NC}"
    echo -e "${YELLOW}Please install Node.js: https://nodejs.org/${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}Found: ${NODE_VERSION}${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm not found${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}Found npm: ${NPM_VERSION}${NC}"

# Check if virtual environment exists
VENV_DIR="problem-solver/py/unified_service/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "${VENV_DIR}/bin/activate"

# Install/upgrade dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
cd problem-solver/py/unified_service
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Set environment variables for API
export OLLAMA_BASE_URL="${OLLAMA_URL}"
export LLM_MODEL="${MODEL}"
export PORT="${API_PORT}"
export PYTHONPATH="${PWD}:${PYTHONPATH}"
export SQLITE_DB_NAME="${PWD}/unified_rag_app.db"
export CHROMA_PERSIST_DIRECTORY="${PWD}/chroma_db"
export LOG_LEVEL="INFO"

# Create necessary directories
mkdir -p chroma_db temp_uploads

# Start the services
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting services...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

# Start API
echo -e "${BLUE}Starting API server...${NC}"
python3 -m uvicorn main:app --host 0.0.0.0 --port "${API_PORT}" --reload > /tmp/ostis-api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}API started (PID: ${API_PID})${NC}"

# Wait a bit for API to start
sleep 2

# Check if API is running
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}Error: API failed to start${NC}"
    echo -e "${YELLOW}Check logs: /tmp/ostis-api.log${NC}"
    exit 1
fi

# Go to frontend directory (from script root)
cd "$SCRIPT_DIR/problem-solver/py/app/frontend" || {
    echo -e "${RED}Error: Cannot find frontend directory${NC}"
    kill $API_PID 2>/dev/null || true
    exit 1
}

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
fi

# Set environment variable for frontend
export VITE_UNIFIED_API_URL="http://localhost:${API_PORT}"

# Start frontend
echo -e "${BLUE}Starting frontend server...${NC}"
npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" > /tmp/ostis-frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started (PID: ${FRONTEND_PID})${NC}"

# Wait a bit for frontend to start
sleep 2

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Frontend failed to start${NC}"
    echo -e "${YELLOW}Check logs: /tmp/ostis-frontend.log${NC}"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}API:${NC}"
echo -e "  ${YELLOW}http://localhost:${API_PORT}${NC}"
echo -e "  ${YELLOW}http://localhost:${API_PORT}/docs${NC} (API Documentation)"
echo ""
echo -e "${BLUE}Frontend:${NC}"
echo -e "  ${YELLOW}http://localhost:${FRONTEND_PORT}${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  API: ${YELLOW}/tmp/ostis-api.log${NC}"
echo -e "  Frontend: ${YELLOW}/tmp/ostis-frontend.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for both processes
wait $API_PID $FRONTEND_PID

