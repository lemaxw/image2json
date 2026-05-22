from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3-vl:8b"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_TEMPERATURE = 0.0
DEFAULT_RETRIES = 1
DEFAULT_MAX_IMAGE_SIDE = 1024


class AnalysisConfig(BaseModel):
    model: str = DEFAULT_MODEL
    ollama_url: str = DEFAULT_OLLAMA_URL
    prompt_file: Path | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    temperature: float = DEFAULT_TEMPERATURE
    retries: int = DEFAULT_RETRIES
    max_image_side: int = DEFAULT_MAX_IMAGE_SIDE


def default_prompt_path() -> Path:
    candidates = [
        Path.cwd() / "prompts" / "vision_analysis.md",
        Path(__file__).resolve().parents[2] / "prompts" / "vision_analysis.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_prompt(prompt_file: Path | None = None) -> str:
    path = prompt_file or default_prompt_path()
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")
