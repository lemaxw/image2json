from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from image2json.config import AnalysisConfig, load_prompt
from image2json.json_utils import analysis_from_model_output
from image2json.models import ImageAnalysis
from image2json.ollama_client import OllamaVisionClient


class ImageAnalyzer:
    def __init__(self, config: AnalysisConfig | None = None, client: OllamaVisionClient | None = None) -> None:
        self.config = config or AnalysisConfig()
        self.client = client or OllamaVisionClient(
            base_url=self.config.ollama_url,
            timeout=self.config.timeout,
            retries=self.config.retries,
        )

    def analyze_path(self, image_path: Path) -> ImageAnalysis:
        path = image_path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Image path is not a file: {path}")
        prompt = load_prompt(self.config.prompt_file)
        raw_output = self.client.analyze_image(
            image_path=path,
            prompt=prompt,
            model=self.config.model,
            temperature=self.config.temperature,
            max_image_side=self.config.max_image_side,
        )
        return analysis_from_model_output(raw_output, image_metadata=_read_image_metadata(path))

    def analyze_bytes(self, image_bytes: bytes, filename: str = "upload") -> ImageAnalysis:
        suffix = Path(filename).suffix or ".img"
        with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
            temp_file.write(image_bytes)
            temp_file.flush()
            return self.analyze_path(Path(temp_file.name))


def _read_image_metadata(image_path: Path) -> dict[str, float | int | str]:
    try:
        with Image.open(image_path) as image:
            width, height = image.size
    except Exception:
        return {"width": 0, "height": 0, "orientation": "", "aspect_ratio": 0.0}

    if width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"
    return {
        "width": width,
        "height": height,
        "orientation": orientation,
        "aspect_ratio": round(width / height, 4) if height else 0.0,
    }
