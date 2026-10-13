"""
Tests written against the CURRENT (pre-async-rewrite) behavior of
app/routers/model.py:
- Ollama/HF are unreachable in CI, so /model/generate falls back to a
  demo-mode / local-knowledge-base string.
- An unknown `provider` value currently returns 500 (bug, fixed in
  feature/async-ai-engine, where this file gets updated to expect 400).
- `tokens_generated` is currently `len(text.split())` (word count), not a
  real tokenizer count (also fixed in feature/async-ai-engine).
"""


async def test_generate_without_token_rejected(client):
    res = await client.post(
        "/model/generate",
        json={"prompt": "hello", "max_tokens": 20, "temperature": 0.5},
    )
    assert res.status_code == 403


async def test_generate_with_invalid_token_rejected(client):
    res = await client.post(
        "/model/generate",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={"prompt": "hello", "max_tokens": 20, "temperature": 0.5},
    )
    assert res.status_code == 401


async def test_generate_with_valid_token_succeeds(client, registered_user):
    res = await client.post(
        "/model/generate",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "What is machine learning?", "max_tokens": 50, "temperature": 0.7},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["generated_text"]
    assert data["model"] == "mistral"
    assert data["provider"] == "ollama"
    assert data["tokens_generated"] == len(data["generated_text"].split())


async def test_generate_rejects_temperature_above_max(client, registered_user):
    res = await client.post(
        "/model/generate",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "test", "max_tokens": 20, "temperature": 5.0},
    )
    assert res.status_code == 422


async def test_generate_rejects_empty_prompt(client, registered_user):
    res = await client.post(
        "/model/generate",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "", "max_tokens": 20, "temperature": 0.5},
    )
    assert res.status_code == 422


async def test_unknown_provider_currently_returns_500(client, registered_user):
    # Current bug: app/routers/model.py defines a route handler named
    # `status` (the /model/status endpoint), which shadows the `status`
    # module imported from fastapi at module scope. The "unknown provider"
    # branch references `status.HTTP_500_INTERNAL_SERVER_ERROR`, which by
    # request time resolves to the shadowed function instead -> AttributeError,
    # which uvicorn turns into a generic 500. Fixed in feature/async-ai-engine
    # (explicit 400 for an unknown provider, and the name collision removed).
    res = await client.post(
        "/model/generate",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "test", "max_tokens": 20, "temperature": 0.5, "provider": "banana"},
    )
    assert res.status_code == 500


async def test_model_status_requires_token(client):
    res = await client.get("/model/status")
    assert res.status_code == 403


async def test_model_status_with_token(client, registered_user):
    res = await client.get(
        "/model/status",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "model" in data
    assert "status" in data
    assert "available" in data
