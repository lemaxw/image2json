import httpx
import pytest
from PIL import Image

from image2json.ollama_client import OllamaError, OllamaVisionClient


def test_read_timeout_error_mentions_timeout(monkeypatch, tmp_path):
    image = tmp_path / "sample.jpg"
    Image.new("RGB", (10, 10), color="white").save(image)

    def fake_post(self, path, json):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = OllamaVisionClient(base_url="http://localhost:11434", timeout=1, retries=0)
    with pytest.raises(OllamaError, match="--timeout 600"):
        client.analyze_image(image_path=image, prompt="prompt", model="qwen3-vl:8b", temperature=0.1)
