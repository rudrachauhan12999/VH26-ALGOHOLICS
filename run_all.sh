#!/bin/bash
# run_all.sh - Run backend and RAG pipeline together locally

set -e

echo "=========================================="
echo "VH26-ALGOHOLICS - Full Stack Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo -e "${BLUE}Python version:${NC}"
python3 --version
echo ""

# ==================== RAG SETUP ====================
echo -e "${BLUE}========== RAG SETUP ==========${NC}"
echo ""

if [ ! -d "rag" ]; then
    echo "❌ rag/ directory not found. Are you in the project root?"
    exit 1
fi

echo -e "${YELLOW}1. Creating RAG virtual environment...${NC}"
if [ ! -d "rag/venv" ]; then
    cd rag
    python3 -m venv venv
    cd ..
else
    echo "   (RAG venv already exists)"
fi

echo ""
echo -e "${YELLOW}2. Activating RAG venv and installing dependencies...${NC}"
source rag/venv/bin/activate
pip install --quiet -r rag/requirements.txt
echo -e "${GREEN}   ✓ RAG dependencies installed${NC}"

echo ""
echo -e "${YELLOW}3. Checking RAG .env file...${NC}"
if [ ! -f "rag/.env" ]; then
    echo "   ⚠️  rag/.env not found. Creating from template..."
    cp rag/.env.example rag/.env
    echo -e "${YELLOW}   📝 Edit rag/.env and add your GROQ_API_KEY!${NC}"
    echo "   GROQ_API_KEY=your_key_here"
else
    echo "   ✓ rag/.env exists"
fi

echo ""
echo -e "${YELLOW}4. Generating demo manuals...${NC}"
python -m rag.demo.build_demo_data
echo -e "${GREEN}   ✓ Demo manuals generated${NC}"

echo ""
echo -e "${YELLOW}5. Building FAISS index from manuals...${NC}"
python -m rag.ingest_manuals
echo -e "${GREEN}   ✓ FAISS index built and persisted${NC}"

deactivate

# ==================== BACKEND SETUP ====================
echo ""
echo -e "${BLUE}========== BACKEND SETUP ==========${NC}"
echo ""

if [ ! -d "backend" ]; then
    echo "❌ backend/ directory not found. Are you in the project root?"
    exit 1
fi

echo -e "${YELLOW}1. Creating backend virtual environment...${NC}"
if [ ! -d "backend/venv" ]; then
    cd backend
    python3 -m venv venv
    cd ..
else
    echo "   (Backend venv already exists)"
fi

echo ""
echo -e "${YELLOW}2. Activating backend venv and installing dependencies...${NC}"
source backend/venv/bin/activate
pip install --quiet -r backend/requirements.txt
echo -e "${GREEN}   ✓ Backend dependencies installed${NC}"

echo ""
echo -e "${YELLOW}3. Checking backend .env file...${NC}"
if [ ! -f "backend/.env" ]; then
    echo "   ⚠️  backend/.env not found. Creating from template..."
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}   📝 Edit backend/.env if needed (optional)${NC}"
else
    echo "   ✓ backend/.env exists"
fi

deactivate

# ==================== READY TO RUN ====================
echo ""
echo -e "${GREEN}=========================================="
echo "✓ Setup Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}To run the full stack:${NC}"
echo ""
echo "  Option 1: Run everything in one terminal (sequential):"
echo "    ${YELLOW}bash run_sequential.sh${NC}"
echo ""
echo "  Option 2: Run in separate terminals (recommended):"
echo ""
echo "    Terminal 1 - RAG server (ingestion already done):"
echo "    ${YELLOW}source rag/venv/bin/activate${NC}"
echo "    ${YELLOW}cd rag && python test_rag.py  # Test the pipeline first${NC}"
echo ""
echo "    Terminal 2 - Backend API:"
echo "    ${YELLOW}source backend/venv/bin/activate${NC}"
echo "    ${YELLOW}cd backend && uvicorn app.main:app --reload${NC}"
echo ""
echo -e "${BLUE}Then test:${NC}"
echo "    ${YELLOW}curl http://localhost:8000/health${NC}"
echo "    ${YELLOW}curl -X POST http://localhost:8000/api/troubleshoot \\${NC}"
echo "    ${YELLOW}  -H 'Content-Type: application/json' \\${NC}"
echo "    ${YELLOW}  -d '{\"query\": \"E101\", \"machine\": \"Machine A\"}'${NC}"
echo ""
echo -e "${BLUE}API Documentation:${NC}"
echo "    ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
