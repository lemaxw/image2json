from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3-vl:8b"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_TEMPERATURE = 0.0
DEFAULT_RETRIES = 1
DEFAULT_MAX_IMAGE_SIDE = 1600
DEFAULT_SHORT_VERSION = True


class AnalysisConfig(BaseModel):
    model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL
    prompt_file: Path | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    temperature: float = DEFAULT_TEMPERATURE
    retries: int = DEFAULT_RETRIES
    max_image_side: int = DEFAULT_MAX_IMAGE_SIDE
    short_version: bool = DEFAULT_SHORT_VERSION


def default_prompt_path(short_version: bool = DEFAULT_SHORT_VERSION) -> Path:
    prompt_name = "vision_analysis_short.md" if short_version else "vision_analysis.md"
    candidates = [
        Path.cwd() / "prompts" / prompt_name,
        Path(__file__).resolve().parents[2] / "prompts" / prompt_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_prompt(prompt_file: Path | None = None, short_version: bool = DEFAULT_SHORT_VERSION) -> str:
    path = prompt_file or default_prompt_path(short_version)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")
