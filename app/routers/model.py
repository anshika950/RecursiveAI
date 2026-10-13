from fastapi import APIRouter, Depends, HTTPException, status
import requests
from app.schemas import GenerateRequest, GenerateResponse, ModelStatus, ModelsListResponse
from app.auth import verify_token
from app.config import settings
from app.models_config import list_all_models_flat, get_model_info

router = APIRouter(prefix="/model", tags=["model"])


def get_ollama_response(prompt: str, max_tokens: int, temperature: float, model: str = "mistral") -> str:
    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.ConnectionError:
        return f"[Demo Mode - Ollama Offline] Based on your prompt: '{prompt}'\n\nThis is a demo response. The actual response would come from the {model} model running in Ollama. The response is being generated with temperature={temperature} and max_tokens={max_tokens}."
    except Exception as e:
        return f"[Demo Mode] Error connecting to model: {str(e)}"


def get_local_response(prompt: str, max_tokens: int, temperature: float) -> str:
    """Generate responses using local knowledge base"""
    prompt_lower = prompt.lower()

    responses = {
        "machine learning": "Machine learning is a type of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves creating algorithms that can identify patterns and make predictions or decisions based on data inputs. The process typically includes training models on historical data, validating their performance, and then using them to make predictions on new, unseen data.",

        "what is ai": "Artificial Intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence. These tasks include learning from experience, recognizing patterns, understanding language, and making decisions. AI systems use algorithms and data to simulate human cognitive functions, and they can be applied to various fields like healthcare, finance, transportation, and education.",

        "deep learning": "Deep learning is a subset of machine learning that uses neural networks with multiple layers to learn complex patterns in data. It's inspired by how the human brain processes information through interconnected neurons. Deep learning has been particularly successful in areas like image recognition, natural language processing, and speech recognition.",

        "neural network": "A neural network is a computational model inspired by biological neurons in the human brain. It consists of interconnected nodes (neurons) organized in layers that process information. Neural networks can learn patterns from data and are particularly effective for complex pattern recognition tasks.",

        "data science": "Data science is an interdisciplinary field that uses scientific methods, processes, algorithms, and systems to extract meaningful insights from data. It combines statistics, programming, domain knowledge, and business acumen to analyze and interpret complex datasets.",

        "algorithm": "An algorithm is a step-by-step procedure or formula for solving a problem or accomplishing a task. In computer science, algorithms are sets of instructions that computers follow to process data and produce outputs. Good algorithms are efficient, correct, and scalable.",
    }

    # Find matching response
    for key, response_text in responses.items():
        if key in prompt_lower:
            return response_text

    # Default response for unknown queries
    return f"Explanation of '{prompt}': This topic explores important concepts in technology and artificial intelligence. To get a specific explanation, try asking about machine learning, artificial intelligence, neural networks, deep learning, or data science."

def get_huggingface_response(prompt: str, max_tokens: int, temperature: float, model: str = "gpt2") -> str:
    if not settings.HF_API_TOKEN:
        # Use local response instead
        return get_local_response(prompt, max_tokens, temperature)

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {settings.HF_API_TOKEN}"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_length": max_tokens,
                    "temperature": temperature
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()[0]["generated_text"]
    except Exception as e:
        # Fall back to local response on error
        return get_local_response(prompt, max_tokens, temperature)


@router.get("/list", response_model=ModelsListResponse)
def list_models(username: str = Depends(verify_token)):
    """List all available models"""
    models = list_all_models_flat()
    return ModelsListResponse(models=[{"id": m["id"], "name": m["name"], "provider": m["provider"], "description": m["description"], "size": m["size"]} for m in models])


@router.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest, username: str = Depends(verify_token)):
    provider = request.provider
    model = request.model

    if provider == "ollama":
        generated_text = get_ollama_response(request.prompt, request.max_tokens, request.temperature, model)
    elif provider == "huggingface":
        generated_text = get_huggingface_response(request.prompt, request.max_tokens, request.temperature, model)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown provider")

    return GenerateResponse(
        generated_text=generated_text,
        model=model,
        provider=provider,
        tokens_generated=len(generated_text.split())
    )


@router.get("/status", response_model=ModelStatus)
def status(username: str = Depends(verify_token)):
    if settings.MODEL_TYPE == "ollama":
        try:
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            available = response.status_code == 200
        except:
            available = False
    else:
        available = bool(settings.HF_API_TOKEN)

    return ModelStatus(
        model=settings.MODEL_NAME,
        status="online" if available else "offline",
        available=available
    )
