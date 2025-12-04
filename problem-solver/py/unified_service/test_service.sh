#!/bin/bash

# Test script for Unified Service

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL=${1:-http://localhost:8000}

echo "=================================="
echo "OSTIS ANN Unified Service Tester"
echo "Base URL: $BASE_URL"
echo "=================================="

# Test 1: Health Check
echo -e "\n${YELLOW}[1/4]${NC} Testing health check..."
RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/health)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓${NC} Health check passed"
    echo "$BODY" | python3 -m json.tool
else
    echo -e "${RED}✗${NC} Health check failed (HTTP $HTTP_CODE)"
    exit 1
fi

# Test 2: Informational Query
echo -e "\n${YELLOW}[2/4]${NC} Testing informational query..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Что такое нейронная сеть?", "session_id": "test-session-1"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓${NC} Informational query test passed"
    echo "$BODY" | python3 -m json.tool | head -n 20
    echo "..."
else
    echo -e "${RED}✗${NC} Informational query test failed (HTTP $HTTP_CODE)"
    echo "$BODY"
fi

# Test 3: Build Model Query (first step)
echo -e "\n${YELLOW}[3/4]${NC} Testing build_model query..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Создай модель для классификации изображений", "session_id": "test-session-2"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓${NC} Build model query test passed"
    echo "$BODY" | python3 -m json.tool | head -n 20
    echo "..."
else
    echo -e "${RED}✗${NC} Build model query test failed (HTTP $HTTP_CODE)"
    echo "$BODY"
fi

# Test 4: Document List
echo -e "\n${YELLOW}[4/4]${NC} Testing document list..."
RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/api/v1/documents/list)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓${NC} Document list test passed"
    echo "$BODY" | python3 -m json.tool
else
    echo -e "${RED}✗${NC} Document list test failed (HTTP $HTTP_CODE)"
fi

# Summary
echo -e "\n=================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "=================================="
echo ""
echo "Additional tests you can run:"
echo ""
echo "1. Upload a document:"
echo "   curl -X POST $BASE_URL/api/v1/documents/upload \\"
echo "     -F 'file=@/path/to/document.pdf'"
echo ""
echo "2. Continue build_model conversation:"
echo "   curl -X POST $BASE_URL/api/v1/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"табличные данные iris\", \"session_id\": \"test-session-2\"}'"
echo ""
echo "3. View API docs:"
echo "   Open $BASE_URL/docs in your browser"
echo ""

