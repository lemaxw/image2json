from __future__ import annotations

import base64
from io import BytesIO
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageOps

from image2json.models import ImageAnalysis


class OllamaError(RuntimeError):
    pass


class OllamaUnavailableError(OllamaError):
    pass


class OllamaModelMissingError(OllamaError):
    pass


class OllamaVisionClient:
    def __init__(self, base_url: str, timeout: float, retries: int = 1) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def analyze_image(
        self,
        *,
        image_path: Path,
        prompt: str,
        model: str,
        temperature: float,
        max_image_side: int = 1600,
    ) -> str:
        image_bytes = _image_bytes_for_ollama(image_path, max_image_side=max_image_side)
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "stream": False,
            "format": ImageAnalysis.model_json_schema(),
            "think": False,
            "options": {"temperature": temperature},
        }

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                    response = client.post("/api/chat", json=payload)
                if response.status_code == 404:
                    raise OllamaModelMissingError(
                        f"Ollama model '{model}' is not available. Run: ollama pull {model}"
                    )
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    message = str(data["error"])
                    if "not found" in message.lower() or "pull" in message.lower():
                        raise OllamaModelMissingError(
                            f"Ollama model '{model}' is not available. Run: ollama pull {model}"
                        )
                    raise OllamaError(message)
                result = _extract_message_content(data)
                if not isinstance(result, str):
                    raise OllamaError("Ollama response did not contain message.content text.")
                if not result.strip():
                    raise OllamaError(
                        "Ollama returned an empty response. Verify this model supports vision through "
                        "/api/chat and try a direct prompt such as: "
                        "ollama run qwen3-vl:8b /path/to/image.jpg 'describe this image'"
                    )
                return result
            except OllamaModelMissingError:
                raise
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise OllamaUnavailableError(
                        f"Could not connect to local Ollama at {self.base_url}. "
                        "Start Ollama and verify the URL."
                    ) from exc
            except httpx.ReadTimeout as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise OllamaError(
                        f"Ollama timed out after {self.timeout:g}s while analyzing the image. "
                        "Local vision models can be slow with large images and detailed schemas. "
                        "Try again with a larger timeout, for example: --timeout 600"
                    ) from exc
            except (httpx.RemoteProtocolError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise OllamaError(f"Ollama request failed after retries: {exc}") from exc
            time.sleep(0.25 * (attempt + 1))
        raise OllamaError(f"Ollama request failed: {last_error}")


def _extract_message_content(data: dict[str, Any]) -> str | None:
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    response = data.get("response")
    if isinstance(response, str):
        return response
    return None


def _image_bytes_for_ollama(image_path: Path, *, max_image_side: int) -> bytes:
    if max_image_side <= 0:
        return image_path.read_bytes()

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        longest = max(width, height)
        if longest <= max_image_side:
            return image_path.read_bytes()

        scale = max_image_side / longest
        resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        resized = image.resize(resized_size, Image.Resampling.LANCZOS)
        if resized.mode not in {"RGB", "L"}:
            resized = resized.convert("RGB")

        buffer = BytesIO()
        resized.save(buffer, format="JPEG", quality=92, optimize=True)
        return buffer.getvalue()
