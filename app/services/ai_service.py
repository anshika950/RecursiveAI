"""Async AI generation with an explicit, labeled fallback tier.

Replaces the old synchronous `requests`-based calls (which blocked the
FastAPI event loop) with `httpx.AsyncClient`. The low-level provider
functions (`call_ollama`, `call_huggingface`) are honest about failure —
they raise `HTTPException(503, ...)` rather than silently returning a
canned string dressed up to look like a real model response. The
orchestrator (`generate_response`) is the only place that decides to fall
back to the local knowledge base, and it always reports that decision back
via `used_fallback=True` instead of hiding it.
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings

KNOWN_PROVIDERS = {"ollama", "huggingface"}

_LOCAL_KNOWLEDGE_BASE = {
    "machine learning": (
        "Machine learning is a type of artificial intelligence that enables "
        "computers to learn and improve from experience without being "
        "explicitly programmed. It involves creating algorithms that can "
        "identify patterns and make predictions or decisions based on data "
        "inputs. The process typically includes training models on "
        "historical data, validating their performance, and then using them "
        "to make predictions on new, unseen data."
    ),
    "what is ai": (
        "Artificial Intelligence (AI) refers to computer systems designed to "
        "perform tasks that typically require human intelligence. These "
        "tasks include learning from experience, recognizing patterns, "
        "understanding language, and making decisions. AI systems use "
        "algorithms and data to simulate human cognitive functions, and they "
        "can be applied to various fields like healthcare, finance, "
        "transportation, and education."
    ),
    "deep learning": (
        "Deep learning is a subset of machine learning that uses neural "
        "networks with multiple layers to learn complex patterns in data. "
        "It's inspired by how the human brain processes information through "
        "interconnected neurons. Deep learning has been particularly "
        "successful in areas like image recognition, natural language "
        "processing, and speech recognition."
    ),
    "neural network": (
        "A neural network is a computational model inspired by biological "
        "neurons in the human brain. It consists of interconnected nodes "
        "(neurons) organized in layers that process information. Neural "
        "networks can learn patterns from data and are particularly "
        "effective for complex pattern recognition tasks."
    ),
    "data science": (
        "Data science is an interdisciplinary field that uses scientific "
        "methods, processes, algorithms, and systems to extract meaningful "
        "insights from data. It combines statistics, programming, domain "
        "knowledge, and business acumen to analyze and interpret complex "
        "datasets."
    ),
    "algorithm": (
        "An algorithm is a step-by-step procedure or formula for solving a "
        "problem or accomplishing a task. In computer science, algorithms "
        "are sets of instructions that computers follow to process data and "
        "produce outputs. Good algorithms are efficient, correct, and "
        "scalable."
    ),
}


def get_local_knowledge_base_response(prompt: str) -> str:
    """Last-resort offline tier. Always labeled via `used_fallback=True`
    by the caller — never returned as if it came from a real model."""
    prompt_lower = prompt.lower()
    for key, response_text in _LOCAL_KNOWLEDGE_BASE.items():
        if key in prompt_lower:
            return response_text
    return (
        f"No local knowledge-base entry matches '{prompt}'. Try asking about "
        "machine learning, artificial intelligence, neural networks, deep "
        "learning, or data science."
    )


async def call_ollama(prompt: str, max_tokens: int, temperature: float, model: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            response.raise_for_status()
            return response.json()["response"]
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama is unreachable at {settings.OLLAMA_BASE_URL}. Is it running?",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama returned an error: {exc.response.text}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama request timed out.",
        ) from exc


async def call_huggingface(prompt: str, max_tokens: int, temperature: float, model: str) -> str:
    if not settings.HF_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hugging Face provider requires HF_API_TOKEN to be configured.",
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={"Authorization": f"Bearer {settings.HF_API_TOKEN}"},
                json={
                    "inputs": prompt,
                    "parameters": {"max_length": max_tokens, "temperature": temperature},
                },
            )
            response.raise_for_status()
            return response.json()[0]["generated_text"]
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hugging Face Inference API is unreachable.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Hugging Face returned an error: {exc.response.text}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hugging Face request timed out.",
        ) from exc


async def generate_response(
    provider: str, model: str, prompt: str, max_tokens: int, temperature: float
) -> tuple[str, bool]:
    """Returns (generated_text, used_fallback)."""
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider '{provider}'. Must be one of {sorted(KNOWN_PROVIDERS)}.",
        )

    try:
        if provider == "ollama":
            text = await call_ollama(prompt, max_tokens, temperature, model)
        else:
            text = await call_huggingface(prompt, max_tokens, temperature, model)
        return text, False
    except HTTPException:
        return get_local_knowledge_base_response(prompt), True
