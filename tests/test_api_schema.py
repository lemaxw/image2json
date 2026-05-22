from fastapi.testclient import TestClient

from image2json.api import app
from image2json.models import ImageAnalysis


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_path_response_schema(monkeypatch, tmp_path):
    image = tmp_path / "sample.jpg"
    image.write_bytes(b"fake image")

    def fake_analyze_path(self, image_path):
        return ImageAnalysis(summary="api path ok", raw_model_output="raw")

    monkeypatch.setattr("image2json.analyzer.ImageAnalyzer.analyze_path", fake_analyze_path)
    response = TestClient(app).post(
        "/analyze/path",
        json={"image_path": str(image), "include_raw": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "api path ok"
    assert payload["raw_model_output"] is None
    assert "subjects" in payload


def test_analyze_upload_response_schema(monkeypatch):
    def fake_analyze_bytes(self, image_bytes, filename="upload"):
        return ImageAnalysis(summary=f"upload {filename}", raw_model_output="raw")

    monkeypatch.setattr("image2json.analyzer.ImageAnalyzer.analyze_bytes", fake_analyze_bytes)
    response = TestClient(app).post(
        "/analyze/upload?include_raw=false",
        files={"file": ("sample.jpg", b"fake image", "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "upload sample.jpg"
    assert payload["raw_model_output"] is None
