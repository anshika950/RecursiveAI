# System Architecture

## Overview

```
┌──────────────────────────────────────────────────────────┐
│                  API Layer (FastAPI routers)              │
│  auth | oauth | model | files | admin                     │
├──────────────────────────────────────────────────────────┤
│                 Business Logic (app/services/)             │
│  auth_service | ai_service | token_service | vector_store  │
├──────────────────────────────────────────────────────────┤
│                     Data Layer                              │
│  SQLAlchemy ORM + SQLite (app/models.py)                    │
├──────────────────────────────────────────────────────────┤
│                   External Services                         │
│  Ollama (local) | Hugging Face Inference API (free tier)   │
└──────────────────────────────────────────────────────────┘
```

## Components

### 1. Authentication (`app/auth.py`, `app/services/auth_service.py`)
- **Password Hashing**: Argon2 via Passlib
- **Token Generation**: JWT (HS256), expiring after `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Token Verification**: `HTTPBearer` security scheme (`verify_token`)
- **Google OAuth** (`app/routers/oauth.py`): redirect → code exchange → userinfo → find-or-create user → issue the same JWT shape as `/auth/login`. Needs real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (see `.env.example`); returns a clean `503` if unset.
- **Rate limiting**: `/auth/register` and `/auth/login` are rate-limited (`slowapi`, keyed by client IP, `AUTH_RATE_LIMIT` setting, default `5/minute`).

### 2. Authorization / RBAC (`app/dependencies.py`, `app/routers/admin.py`)
- `User.role` is one of `UserRole.USER` / `PRO` / `ADMIN`.
- `require_role([...])` is a dependency factory that 403s a request if the authenticated user's role isn't in the allowed list.
- `/admin/users` and `/admin/stats` (both `ADMIN`-only) are the first consumers of it.

### 3. AI Generation (`app/services/ai_service.py`, `app/routers/model.py`)
- `call_ollama`/`call_huggingface` are **async** (`httpx.AsyncClient`), so a slow/unreachable model backend no longer blocks the event loop for other requests.
- They raise `HTTPException(503)` on failure rather than returning a canned string. The orchestrator, `generate_response()`, is the only place that falls back to a local offline knowledge base on failure — and it always reports that via `used_fallback=True` on the response, never silently.
- An unknown `provider` value returns a clean `400` naming the bad value.
- `POST /model/generate/stream` streams tokens over SSE (Ollama only — the free HF Inference API doesn't support streaming).
- Token counts (`tokens_generated`) are real `tiktoken` counts (`app/services/token_service.py`), with a word-count fallback if the encoding can't be loaded.
- Every generate call is logged to `GenerationLog` (prompt, response, model, provider, tokens, whether the fallback was used).

### 4. Retrieval-Augmented Generation (`app/services/vector_store.py`, `app/routers/files.py`)
- `POST /files/upload`: accepts `.txt`/`.md`/`.json`/`.csv`, up to 5MB, chunks the text (fixed-size overlapping windows) and stores the chunks.
- `POST /model/generate-with-context`: retrieves the current user's most relevant chunks for the prompt and injects them as context before generating. Retrieval is **TF-IDF (scikit-learn) + cosine similarity**, refit at search time — not neural embeddings (e.g. `sentence-transformers`) or a dedicated vector database (Chroma/FAISS). That's a deliberate choice: neural embedding models are normally downloaded from the Hugging Face Hub on first use, and this project's deployment environment can't reach `huggingface.co`. TF-IDF needs no pretrained weights, so it actually runs. It's a real, working vector-search implementation — just not a neural one — and is swappable later if Hub access is available.

### 5. Data Layer (`app/database.py`, `app/models.py`)
- **ORM**: SQLAlchemy 2.0, SQLite by default (`DATABASE_URL`).
- Tables: `users`, `generation_logs`, `documents`, `document_chunks`.
- Tables are created at startup via `Base.metadata.create_all()` (in the `lifespan` handler in `app/main.py`) — there's no migration tool yet. See `MIGRATIONS.md` for what that means for schema changes in dev.

### 6. Data Validation (`app/schemas.py`)
- Pydantic v2 models for every request/response body — field length limits, numeric ranges (e.g. `temperature` 0.0–2.0), email format, etc.

## Authentication Flow

```
1. Register (password) or OAuth (Google) → account created, password-based
   accounts get an Argon2 hash; OAuth-only accounts get a sentinel value
   that can never match a real password.
2. Login → JWT issued (HS256, "sub" = username, expires in
   ACCESS_TOKEN_EXPIRE_MINUTES).
3. Client sends the token: Authorization: Bearer <token>
4. verify_token() checks the signature + expiry, returns the username.
5. get_current_user_object() (app/dependencies.py) loads the full User row
   for routes that need role/quota info, not just the username.
6. require_role([...]) 403s if the user's role isn't allowed.
```

## Model Integration

### Ollama (local)
- `OLLAMA_BASE_URL` (default `http://localhost:11434`), models like `mistral`, `llama2`, `orca-mini`.
- Supports streaming (`/model/generate/stream`).

### Hugging Face Inference API (free tier)
- Requires `HF_API_TOKEN`. No streaming support used here.

### Local knowledge base (last-resort fallback)
- A small built-in Q&A dictionary (`app/services/ai_service.py`), used only when the requested provider fails — always reported via `used_fallback: true`, never silently.

## Deployment

### Docker
- Multi-stage `Dockerfile`: deps installed in a builder stage, copied into a slim runtime stage running as a non-root user, with a `HEALTHCHECK` against `/health`.
- `docker-compose.yml` loads `.env` via `env_file` rather than hardcoding secrets in the compose file itself.
- CI (`.github/workflows/ci.yml`) runs the full `pytest` suite with coverage on every push/PR to `main`/`develop`.

### Environment Configuration
See `.env.example` for the full list, including the Google OAuth variables and `AUTH_RATE_LIMIT`.

## Security Considerations

1. **JWT Tokens**: HS256-signed, short-lived (`ACCESS_TOKEN_EXPIRE_MINUTES`).
2. **Password Hashing**: Argon2 (via Passlib) — not Bcrypt.
3. **Rate limiting**: `/auth/register` and `/auth/login` are rate-limited per client IP.
4. **CORS**: Currently permissive (`allow_origins=["*"]`) — fine for local dev/demo, should be locked down for a real deployment.
5. **Input Validation**: Pydantic v2 schema validation on every request body.
6. **Secret Key**: `SECRET_KEY` must be set (no default) and changed for any real deployment.
7. **No Alembic**: schema changes in dev require dropping `app.db` — see `MIGRATIONS.md`.
