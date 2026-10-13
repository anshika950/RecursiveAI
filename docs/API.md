# API Reference

Base URL: `http://localhost:8000`

## Authentication Endpoints

Both of these are rate-limited (default `5/minute` per client IP, see `AUTH_RATE_LIMIT`).

### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password_123",
  "email": "john@example.com"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Login User
```http
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password_123"
}
```

**Response (200):** same shape as register.

### Google OAuth
```http
GET /auth/oauth/google/login
```
Redirects to Google's consent screen. Needs `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` configured (see `.env.example`) — returns `503` if not.

```http
GET /auth/oauth/google/callback?code=...
```
Exchanges the code, finds-or-creates the user, returns a `Token` (same shape as `/auth/login`).

---

## Model Endpoints

All require `Authorization: Bearer {access_token}`.

### Generate Text
```http
POST /model/generate
Content-Type: application/json

{
  "prompt": "What is machine learning?",
  "max_tokens": 100,
  "temperature": 0.7,
  "provider": "ollama",
  "model": "mistral"
}
```

**Parameters:**
- `prompt` (string, required, 1–1000 chars)
- `max_tokens` (integer, default 100, 1–2000)
- `temperature` (float, default 0.7, 0.0–2.0)
- `provider` (string, default `"ollama"`, must be `"ollama"` or `"huggingface"` — anything else returns `400`)
- `model` (string, default `"mistral"`)

**Response (200):**
```json
{
  "generated_text": "Machine learning is...",
  "model": "mistral",
  "provider": "ollama",
  "tokens_generated": 45,
  "used_fallback": false
}
```
`used_fallback: true` means the requested provider was unreachable and this is the local offline knowledge-base answer, not the real model's.

### Generate Text (Streaming)
```http
POST /model/generate/stream
```
Same request body as above. Response is `text/event-stream`, one `data: {"token": "..."}` line per generated token, ending with `data: [DONE]`. **Ollama only.**

### Generate With Retrieved Context (RAG)
```http
POST /model/generate-with-context
```
Same request body as `/model/generate`. Retrieves the current user's most relevant uploaded-document chunks for the prompt (TF-IDF + cosine similarity) and injects them as context before generating.

**Response (200):** same as `/model/generate`, plus:
```json
{
  "context_chunks": ["...retrieved chunk 1...", "...retrieved chunk 2..."]
}
```
`context_chunks` is `[]` if the user has no uploaded documents or none matched.

### Check Model Status
```http
GET /model/status
```
```json
{
  "model": "mistral",
  "status": "online",
  "available": true
}
```

### List Available Models
```http
GET /model/list
```

---

## File Endpoints

All require `Authorization: Bearer {access_token}`.

### Upload a Document
```http
POST /files/upload
Content-Type: multipart/form-data

file: <your-file>
```
Allowed extensions: `.txt`, `.md`, `.json`, `.csv`. Max size: 5MB.

**Response (200):**
```json
{
  "document_id": 1,
  "filename": "notes.txt",
  "size_kb": 2.4,
  "chunk_count": 5
}
```

### List My Documents
```http
GET /files/
```
```json
[
  {"document_id": 1, "filename": "notes.txt", "created_at": "2026-01-01T00:00:00Z"}
]
```

---

## Admin Endpoints

Both require `Authorization: Bearer {access_token}` for a user whose `role` is `admin` — a non-admin token gets `403`.

### List Users
```http
GET /admin/users
```

### Generation Stats
```http
GET /admin/stats
```
```json
{
  "total_requests": 42,
  "total_tokens_used": 1337,
  "fallback_responses": 3
}
```

---

## Health Endpoints

### Health Check
```http
GET /health
```
```json
{"status": "healthy"}
```

### Root Endpoint
```http
GET /
```

---

## Error Responses

### 400 Bad Request
```json
{"detail": "Username already registered"}
```
Also used for an unknown `provider` value, bad file extension, or empty upload.

### 401 Unauthorized
```json
{"detail": "Invalid credentials"}
```
Also returned for an invalid/expired JWT.

### 403 Forbidden
Returned when no `Authorization` header is present at all (FastAPI's `HTTPBearer` default), and by `require_role(...)` when an authenticated user's role doesn't match.

### 429 Too Many Requests
Returned by `/auth/register` and `/auth/login` once the rate limit is exceeded.

### 503 Service Unavailable
```json
{"detail": "Ollama is unreachable at http://localhost:11434. Is it running?"}
```
Also returned by the Google OAuth endpoints if `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` aren't configured.

---

## Interactive Documentation

- **Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
