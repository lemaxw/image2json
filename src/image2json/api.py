from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from image2json.analyzer import ImageAnalyzer
from image2json.config import (
    AnalysisConfig,
    DEFAULT_MAX_IMAGE_SIDE,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_SHORT_VERSION,
    DEFAULT_TIMEOUT_SECONDS,
)
from image2json.models import ImageAnalysis
from image2json.ollama_client import OllamaError

app = FastAPI(title="image2json", version="0.1.0")


class AnalyzePathRequest(BaseModel):
    image_path: str
    model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL
    prompt_file: str | None = None
    include_raw: bool = True
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_image_side: int = DEFAULT_MAX_IMAGE_SIDE
    short_version: bool = DEFAULT_SHORT_VERSION


def _strip_raw(analysis: ImageAnalysis, include_raw: bool) -> ImageAnalysis:
    if include_raw:
        return analysis
    clone = analysis.model_copy(deep=True)
    clone.raw_model_output = None
    return clone


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze/upload", response_model=ImageAnalysis)
async def analyze_upload(
    file: UploadFile = File(...),
    model: str = Query(DEFAULT_MODEL),
    ollama_url: str = Query(DEFAULT_OLLAMA_URL),
    prompt_file: str | None = Query(None),
    include_raw: bool = Query(True),
    timeout: float = Query(DEFAULT_TIMEOUT_SECONDS),
    max_image_side: int = Query(DEFAULT_MAX_IMAGE_SIDE),
    short_version: bool = Query(DEFAULT_SHORT_VERSION),
) -> ImageAnalysis:
    try:
        config = AnalysisConfig(
            model=model,
            ollama_url=ollama_url,
            prompt_file=Path(prompt_file) if prompt_file else None,
            timeout=timeout,
            max_image_side=max_image_side,
            short_version=short_version,
        )
        content = await file.read()
        analysis = ImageAnalyzer(config).analyze_bytes(content, file.filename or "upload")
        return _strip_raw(analysis, include_raw)
    except (FileNotFoundError, ValueError, OllamaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/analyze/path", response_model=ImageAnalysis)
def analyze_path(request: AnalyzePathRequest) -> ImageAnalysis:
    try:
        config = AnalysisConfig(
            model=request.model,
            ollama_url=request.ollama_url,
            prompt_file=Path(request.prompt_file) if request.prompt_file else None,
            timeout=request.timeout,
            max_image_side=request.max_image_side,
            short_version=request.short_version,
        )
        analysis = ImageAnalyzer(config).analyze_path(Path(request.image_path))
        return _strip_raw(analysis, request.include_raw)
    except (FileNotFoundError, ValueError, OllamaError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
