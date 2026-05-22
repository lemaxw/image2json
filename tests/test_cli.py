import json

from typer.testing import CliRunner

from image2json import cli
from image2json.models import ImageAnalysis
from image2json.ollama_client import OllamaError


def test_cli_analyze_schema_shape(monkeypatch, tmp_path):
    image = tmp_path / "sample.jpg"
    image.write_bytes(b"fake image")

    def fake_analyze_path(self, image_path):
        return ImageAnalysis(summary="cli ok", raw_model_output="raw")

    monkeypatch.setattr("image2json.analyzer.ImageAnalyzer.analyze_path", fake_analyze_path)
    result = CliRunner().invoke(cli.app, ["analyze", str(image), "--no-raw", "--compact"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["summary"] == "cli ok"
    assert payload["raw_model_output"] is None
    assert "validation_warnings" in payload


def test_cli_analyze_ollama_error_is_clean(monkeypatch, tmp_path):
    image = tmp_path / "sample.jpg"
    image.write_bytes(b"fake image")

    def fake_analyze_path(self, image_path):
        raise OllamaError("Ollama timed out after 300s. Try again with --timeout 600")

    monkeypatch.setattr("image2json.analyzer.ImageAnalyzer.analyze_path", fake_analyze_path)
    result = CliRunner().invoke(cli.app, ["analyze", str(image)])

    assert result.exit_code == 1
    assert "Ollama timed out" in result.stderr
    assert "Traceback" not in result.stderr
