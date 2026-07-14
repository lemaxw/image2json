from image2json.inference_schema import MODEL_RESPONSE_SCHEMA
from image2json.models import ImageAnalysis


def test_inference_schema_is_compact_and_preserves_required_analysis_sections():
    required = set(MODEL_RESPONSE_SCHEMA["required"])
    assert {
        "subjects",
        "composition",
        "spatial_map",
        "dynamic_potential",
        "soundscape",
        "reframe_constraints",
        "generation_risks",
    } <= required
    assert "image_metadata" not in required
    assert len(str(MODEL_RESPONSE_SCHEMA)) < len(str(ImageAnalysis.model_json_schema()))
