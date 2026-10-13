# RecursiveAI 🧠

![CI](https://github.com/anshika950/RecursiveAI/actions/workflows/ci.yml/badge.svg?branch=main)

A containerized FastAPI microservice running open models locally or via free-tier APIs, protected by JWT authentication, role-based access control, and Pydantic v2 schema validation — with retrieval-augmented generation over your own uploaded documents.

**RecursiveAI** - Intelligent text generation at your fingertips. Powered by open models, secured with JWT.

## Features

- **FastAPI** - Modern async web framework, async AI provider calls (no blocking I/O)
- **JWT Authentication** - Argon2-hashed passwords, HS256 tokens, rate-limited login/register
- **Google OAuth** - Sign in with Google (needs your own OAuth credentials — see below)
- **Role-Based Access Control** - `USER`/`PRO`/`ADMIN` roles, admin-only endpoints
- **Pydantic v2** - Data validation and serialization
- **Open Model Integration** - Ollama (local) or Hugging Face API (free-tier), with an explicitly-labeled offline fallback (`used_fallback`) if neither is reachable
- **Streaming generation** - Server-Sent Events for Ollama
- **File upload + RAG** - Upload `.txt`/`.md`/`.json`/`.csv` documents, ask questions against them (TF-IDF + cosine similarity retrieval)
- **Structured JSON logging**
- **Docker** - Multi-stage build, non-root user, healthcheck
- **CI** - GitHub Actions runs the full pytest suite with coverage on every push/PR

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- (Optional) Ollama for local model execution

### Installation

```bash
# Clone the repo
git clone https://github.com/anshika950/RecursiveAI.git
cd RecursiveAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Set environment variables
cp .env.example .env

# Run the server
uvicorn app.main:app --reload
```

Server will be available at: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### Running with Docker

```bash
docker-compose up --build
```

### Running Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q --cov=app --cov-report=term-missing tests/
```

## API Endpoints

See [docs/API.md](./docs/API.md) for full request/response examples.

### Authentication
- `POST /auth/register` - Register new user (rate-limited)
- `POST /auth/login` - Get JWT token (rate-limited)
- `GET /auth/oauth/google/login` / `GET /auth/oauth/google/callback` - Google OAuth

### AI Model
- `POST /model/generate` - Generate text
- `POST /model/generate/stream` - Streaming generation (Ollama only)
- `POST /model/generate-with-context` - RAG: generate using your uploaded documents as context
- `GET /model/status` - Check model availability
- `GET /model/list` - List available models

### Files
- `POST /files/upload` - Upload a document for RAG
- `GET /files/` - List your uploaded documents

### Admin (requires `ADMIN` role)
- `GET /admin/users` - List all users
- `GET /admin/stats` - Aggregate generation stats

## Google OAuth Setup

Google sign-in needs real credentials from your own Google Cloud project:

1. Go to [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
2. Create an **OAuth client ID**, type "Web application"
3. Add `http://localhost:8000/auth/oauth/google/callback` as an authorized redirect URI
4. Put the resulting Client ID/Secret into `.env` as `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`

Without these set, `/auth/oauth/google/*` returns a clean `503` rather than crashing.

## Documentation

- [Architecture](./docs/ARCHITECTURE.md) - System design and components
- [API Reference](./docs/API.md) - Detailed API documentation
- [Setup Guide](./docs/SETUP.md) - Deployment and configuration
- [Migrations](./MIGRATIONS.md) - Why there's no Alembic yet, and what that means for schema changes

## Project Structure

```
RecursiveAI/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware, rate limiter
│   ├── config.py                # Environment variables / settings
│   ├── auth.py                  # Password hashing, JWT create/verify
│   ├── dependencies.py          # get_current_user_object, require_role
│   ├── rate_limit.py            # Shared slowapi Limiter instance
│   ├── logging_config.py        # Structured JSON logging setup
│   ├── database.py              # SQLAlchemy engine/session
│   ├── models.py                # User, GenerationLog, Document, DocumentChunk
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── services/
│   │   ├── auth_service.py      # Register/login business logic
│   │   ├── ai_service.py        # Async Ollama/HF calls + offline fallback
│   │   ├── token_service.py     # tiktoken-based token counting
│   │   └── vector_store.py      # Chunking + TF-IDF retrieval for RAG
│   └── routers/
│       ├── auth.py              # Register/login endpoints
│       ├── oauth.py             # Google OAuth endpoints
│       ├── model.py             # Generate / stream / RAG / status endpoints
│       ├── files.py             # Document upload/list endpoints
│       └── admin.py             # Admin-only endpoints
├── tests/                       # pytest suite (httpx AsyncClient against the ASGI app)
├── .github/workflows/ci.yml     # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    └── SETUP.md
```

## Environment Variables

See `.env.example` for required variables, including the Google OAuth and rate-limit settings.

## License

MIT
