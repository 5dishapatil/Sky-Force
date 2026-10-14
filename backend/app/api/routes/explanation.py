"""LLM Explanation API routes."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.explanation.service import ExplanationService

router = APIRouter(prefix="/explain", tags=["Explainability"])
service = ExplanationService()


@router.post("", response_model=ExplanationResponse)
def generate_explanation(req: ExplanationRequest) -> ExplanationResponse:
    """Generates an evidence-grounded natural language explanation for routing, weather, or QA."""
    return service.explain(
        task=req.task,
        context=req.context_data,
        query=req.user_query,
    )


@router.get("/status")
def get_explanation_engine_status() -> dict[str, Any]:
    """Returns whether local Ollama & Phi-3 are active or if deterministic fallback is running."""
    settings = get_settings()
    is_available = service.check_ollama_availability()
    return {
        "ollama_available": is_available,
        "active_engine": settings.ollama_model if is_available else "deterministic_fallback",
        "model_name": settings.ollama_model,
        "ollama_url": settings.ollama_base_url,
    }

