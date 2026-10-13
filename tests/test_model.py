"""
Updated for feature/async-ai-engine. The provider calls are now async
(httpx) and genuinely fail with a 503 when Ollama/HF aren't reachable
(true in this test environment), at which point the orchestrator falls
back to the local knowledge base and reports that explicitly via
`used_fallback=True` — it's never silently returned as if it were a
real model response. An unknown `provider` now cleanly returns 400
(previously crashed with an AttributeError -> generic 500, caused by a
module-level name collision that's fixed as part of this same branch).
`tokens_generated` is now a real tiktoken count, not a word count.
"""

from app.services import token_service


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


async def test_generate_falls_back_when_ollama_unreachable(client, registered_user):
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
    assert data["used_fallback"] is True
    assert data["tokens_generated"] == token_service.count_tokens(data["generated_text"])


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


async def test_unknown_provider_returns_400(client, registered_user):
    res = await client.post(
        "/model/generate",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "test", "max_tokens": 20, "temperature": 0.5, "provider": "banana"},
    )
    assert res.status_code == 400
    assert "banana" in res.json()["detail"]


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


async def test_generate_stream_endpoint_responds(client, registered_user):
    res = await client.post(
        "/model/generate/stream",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "hi", "max_tokens": 10, "temperature": 0.5},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "data:" in res.text
