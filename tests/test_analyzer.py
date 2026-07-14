from PIL import Image

from image2json.analyzer import ImageAnalyzer
from image2json.analyzer import _read_image_metadata
from image2json.config import AnalysisConfig


def test_read_image_metadata(tmp_path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (120, 80), color="white").save(image_path)

    metadata = _read_image_metadata(image_path)

    assert metadata == {
        "width": 120,
        "height": 80,
        "orientation": "landscape",
        "aspect_ratio": 1.5,
    }


def test_analyzer_uses_short_prompt_by_default(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (4, 4), color="white").save(image_path)
    seen: dict[str, object] = {}

    def fake_load_prompt(prompt_file=None, short_version=False):
        seen["short_version"] = short_version
        return "prompt"

    class FakeClient:
        def analyze_image(self, **kwargs):
            seen["prompt"] = kwargs["prompt"]
            return '{"summary": "ok", "detailed_description": "details"}'

    monkeypatch.setattr("image2json.analyzer.load_prompt", fake_load_prompt)

    analysis = ImageAnalyzer(client=FakeClient()).analyze_path(image_path)

    assert seen == {"short_version": True, "prompt": "prompt"}
    assert analysis.summary == "ok"


def test_analyzer_uses_documented_image_size_default(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (4, 4), color="white").save(image_path)
    seen: dict[str, object] = {}

    class FakeClient:
        def analyze_image(self, **kwargs):
            seen["max_image_side"] = kwargs["max_image_side"]
            return '{"summary": "ok"}'

    analysis = ImageAnalyzer(client=FakeClient()).analyze_path(image_path)

    assert seen["max_image_side"] == 1600
    assert analysis.summary == "ok"


def test_analyzer_can_select_full_prompt(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (4, 4), color="white").save(image_path)
    seen: dict[str, object] = {}

    def fake_load_prompt(prompt_file=None, short_version=False):
        seen["short_version"] = short_version
        return "prompt"

    class FakeClient:
        def analyze_image(self, **kwargs):
            return '{"summary": "ok"}'

    monkeypatch.setattr("image2json.analyzer.load_prompt", fake_load_prompt)

    ImageAnalyzer(config=AnalysisConfig(short_version=False), client=FakeClient()).analyze_path(image_path)

    assert seen == {"short_version": False}
