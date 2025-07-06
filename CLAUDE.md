# CLAUDE.md
中文对话。
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Backend Development
```bash
# Start the backend from backend directory (recommended)
cd backend
../start_backend.sh

# Start with custom port
../start_backend.sh --port 8080

# Start from project root
./start_backend.sh --from-root

# Direct uvicorn (from backend directory)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
# Start frontend development server
cd frontend-app
npm run dev      # Starts on port 5173

# Build frontend
npm run build

# Lint frontend code
npm run lint
```

### Testing
```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/

# Run tests using project test runner
python scripts/testing/run_tests.py --type all
python scripts/testing/run_tests.py --type unit
python scripts/testing/run_tests.py --type integration
```

### Code Quality
```bash
# Format code
cd backend
black .
isort .

# Type checking
mypy backend/app

# Code linting
ruff check backend/app
```

### Database Management
```bash
# Initialize databases
./scripts/database/init_db.sh

# Create admin user
python scripts/backend/create_admin.py
```

## Project Architecture

### High-Level Structure
This is a RAG (Retrieval-Augmented Generation) chat system with a microservices architecture:

- **Backend**: FastAPI + Python 3.10 with dependency injection pattern
- **Frontend**: React + TypeScript + TailwindCSS
- **Databases**: MongoDB (metadata), Milvus (vectors), Redis (cache)
- **AI Models**: OpenAI GPT + Embedding models

### Key Components

#### RAG Pipeline (backend/app/rag/)
The RAG system is componentized with pluggable interfaces:
- **DocumentLoader**: Multi-format document processing (PDF, TXT, MD)
- **TextSplitter**: Parent-child chunking with independent numbering
- **Embedder**: Vector embedding generation (OpenAI/local models)
- **Retriever**: High-performance vector search via Milvus
- **Generator**: LLM response generation
- **RagPipeline**: Orchestrates the entire flow

#### Dependency Injection Architecture
The system uses FastAPI's dependency injection extensively:
```python
# All dependencies are provided through app/dependencies.py
from app.dependencies import (
    get_rag_pipeline,
    get_document_loader,
    get_text_splitter,
    # ... other dependencies
)

# Used in API routes like:
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    rag_pipeline: IRagPipeline = Depends(get_rag_pipeline)
):
```

#### API Structure (24 endpoints)
- **Authentication**: `/api/auth/*` - JWT-based authentication
- **Documents**: `/api/v1/documents/*` - Document upload and management
- **RAG**: `/api/v1/rag/*` - Question answering and retrieval
- **Collections**: `/api/v1/document-collections/*` - Document grouping
- **Admin**: `/api/admin/*` - System management

### Data Flow
```
Document Upload → Processing → Chunking → Embedding → Vector Storage (Milvus)
User Query → Embedding → Vector Search → LLM Generation → Response
```

### Key Directories
- `backend/app/api/v1/` - API route definitions
- `backend/app/services/` - Business logic services
- `backend/app/rag/` - RAG core components and interfaces
- `backend/app/core/config.py` - Centralized configuration
- `backend/app/dependencies.py` - Dependency injection setup
- `frontend-app/src/` - React frontend application

### Testing Strategy
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and component interactions
- **Test Coverage**: Currently 91.7% pass rate (11/12 tests)
- **Test Data**: Managed through `backend/tests/fixtures/` and `backend/tests/data/`

### Configuration Management
- Environment-specific configs in `.env` files
- Centralized config in `backend/app/core/config.py`
- Docker configurations in `docker-compose.yml` and `docker-compose.prod.yml`
- Python project config in `pyproject.toml`

### Important Notes
- Always use dependency injection for services and components
- Follow the existing patterns for new RAG components
- Backend should be started from the `backend/` directory for proper imports
- The system uses parent-child document chunking for better retrieval precision
- All file paths in code should be handled through `backend/app/core/paths.py`
- API responses follow consistent patterns defined in schemas