import json

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import verify_token
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_object
from app.models import GenerationLog, User
from app.models_config import list_all_models_flat
from app.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateWithContextResponse,
    ModelsListResponse,
    ModelStatus,
)
from app.services import ai_service, token_service, vector_store

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/list", response_model=ModelsListResponse)
def list_models(username: str = Depends(verify_token)):
    """List all available models"""
    models = list_all_models_flat()
    return ModelsListResponse(models=[{"id": m["id"], "name": m["name"], "provider": m["provider"], "description": m["description"], "size": m["size"]} for m in models])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_object),
):
    generated_text, used_fallback = await ai_service.generate_response(
        request.provider, request.model, request.prompt, request.max_tokens, request.temperature
    )
    tokens_generated = token_service.count_tokens(generated_text)

    db.add(
        GenerationLog(
            username=current_user.username,
            prompt=request.prompt,
            response=generated_text,
            model_name=request.model,
            provider=request.provider,
            tokens_used=tokens_generated,
            used_fallback=1 if used_fallback else 0,
        )
    )
    current_user.tokens_consumed = (current_user.tokens_consumed or 0) + tokens_generated
    db.commit()

    return GenerateResponse(
        generated_text=generated_text,
        model=request.model,
        provider=request.provider,
        tokens_generated=tokens_generated,
        used_fallback=used_fallback,
    )


@router.post("/generate-with-context", response_model=GenerateWithContextResponse)
async def generate_with_context(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_object),
):
    """Retrieval-augmented generation: retrieves the current user's most
    relevant uploaded-document chunks for this prompt (TF-IDF + cosine
    similarity, see app/services/vector_store.py) and injects them as
    context before generating."""
    context_chunks = vector_store.search(db, request.prompt, current_user.username, top_k=3)

    if context_chunks:
        context_block = "\n\n".join(context_chunks)
        augmented_prompt = f"Context:\n{context_block}\n\nQuestion: {request.prompt}\n\nAnswer:"
    else:
        augmented_prompt = request.prompt

    generated_text, used_fallback = await ai_service.generate_response(
        request.provider, request.model, augmented_prompt, request.max_tokens, request.temperature
    )
    tokens_generated = token_service.count_tokens(generated_text)

    db.add(
        GenerationLog(
            username=current_user.username,
            prompt=augmented_prompt,
            response=generated_text,
            model_name=request.model,
            provider=request.provider,
            tokens_used=tokens_generated,
            used_fallback=1 if used_fallback else 0,
        )
    )
    current_user.tokens_consumed = (current_user.tokens_consumed or 0) + tokens_generated
    db.commit()

    return GenerateWithContextResponse(
        generated_text=generated_text,
        model=request.model,
        provider=request.provider,
        tokens_generated=tokens_generated,
        used_fallback=used_fallback,
        context_chunks=context_chunks,
    )


@router.post("/generate/stream")
async def generate_stream(request: GenerateRequest, username: str = Depends(verify_token)):
    """SSE streaming generation. Ollama-only — the free Hugging Face
    Inference API used elsewhere in this project doesn't support streaming."""

    async def event_generator():
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": True,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        yield f"data: {json.dumps({'token': data.get('response', '')})}\n\n"
                        if data.get("done", False):
                            yield "data: [DONE]\n\n"
                            return
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': f'Ollama is unreachable at {settings.OLLAMA_BASE_URL}'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/status", response_model=ModelStatus)
async def model_status(username: str = Depends(verify_token)):
    if settings.MODEL_TYPE == "ollama":
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                available = response.status_code == 200
        except Exception:
            available = False
    else:
        available = bool(settings.HF_API_TOKEN)

    return ModelStatus(
        model=settings.MODEL_NAME,
        status="online" if available else "offline",
        available=available,
    )
