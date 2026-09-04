# VH26-ALGOHOLICS - Machine Troubleshooting System

RAG-based intelligent machine troubleshooting assistant for technicians. This system uses AI to help diagnose and resolve machine errors by querying manuals and maintenance documentation.

## Project Structure

```
VH26-ALGOHOLICS/
├── backend/          # FastAPI REST API server
├── rag/             # RAG pipeline (ingestion, retrieval, generation)
└── README.md        # This file
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### 1. Backend Setup and Run

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
copy .env.example .env    # Windows
# or
cp .env.example .env      # macOS/Linux

# Run the backend server
uvicorn app.main:app --reload
```

**Backend will be available at:**
- API Base: http://localhost:8000
- Interactive API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 2. RAG Pipeline Setup (Optional)

```bash
# Navigate to RAG directory
cd rag

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy .env.example .env    # Windows (edit with your API keys)
# or
cp .env.example .env      # macOS/Linux (edit with your API keys)

# Ingest demo manuals
python ingest_manuals.py

# Test RAG pipeline
python test_rag.py
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Troubleshoot Machine Issue
```bash
curl -X POST http://localhost:8000/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "E101", "machine": "Machine A", "model": "X200"}'
```

### List Available Machines
```bash
curl http://localhost:8000/api/machines
```

### List Available Manuals
```bash
curl http://localhost:8000/api/manuals
```

### Upload Manual
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/manual.pdf"
```

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### RAG Tests
```bash
cd rag
python test_rag.py
```

## Development

### Backend Structure
- `app/main.py` - FastAPI application entry point
- `app/routes/` - API route handlers
- `app/models/schemas.py` - Request/response models
- `app/services/rag_service.py` - RAG integration layer
- `tests/` - API tests

### RAG Structure
- `pipeline.py` - Main RAG orchestration
- `ingestion/` - PDF loading and parsing
- `chunking/` - Document chunking strategies
- `embeddings/` - Embedding generation
- `retrieval/` - Vector search and retrieval
- `generation/` - LLM-based response generation
- `conversation/` - Conversation memory management

## Environment Variables

### Backend (.env)
```
FRONTEND_URL=http://localhost:5173
```

### RAG (.env)
```
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX=machine-manuals
```

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, specify a different port:
```bash
uvicorn app.main:app --reload --port 8001
```

### Module Not Found Errors
Make sure your virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### RAG API Key Errors
Ensure your `.env` file in the `rag/` directory contains valid API keys for Groq and Pinecone.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## License

[Add your license information here]
