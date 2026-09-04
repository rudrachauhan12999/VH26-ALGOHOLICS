#!/bin/bash
# run_sequential.sh - Run RAG ingestion, then backend sequentially in one terminal

set -e

echo "=========================================="
echo "VH26-ALGOHOLICS - Sequential Runner"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ==================== RAG ====================
echo -e "${BLUE}[1/3] Starting RAG Pipeline...${NC}"
echo ""

source rag/venv/bin/activate

echo -e "${YELLOW}Testing RAG pipeline...${NC}"
python rag/test_rag.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ RAG pipeline tests passed${NC}"
else
    echo -e "${RED}✗ RAG pipeline tests failed${NC}"
    exit 1
fi

echo ""
deactivate

# ==================== BACKEND ====================
echo -e "${BLUE}[2/3] Starting Backend API...${NC}"
echo ""

source backend/venv/bin/activate

cd backend

echo -e "${YELLOW}Running backend on http://localhost:8000${NC}"
echo -e "${YELLOW}Docs available at http://localhost:8000/docs${NC}"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Note: This script blocks here. When you stop the backend (Ctrl+C),
# it will print a summary.
