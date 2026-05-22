from image2json.json_utils import analysis_from_model_output
from image2json.models import ImageAnalysis, SCHEMA_VERSION


def test_image_analysis_defaults_are_stable():
    analysis = ImageAnalysis()
    assert analysis.schema_version == SCHEMA_VERSION
    assert analysis.image_metadata.width == 0
    assert analysis.subjects == []
    assert analysis.scene.environment == ""
    assert analysis.spatial_map.primary_regions == []
    assert analysis.dynamic_potential.natural_motion_elements == []
    assert analysis.reframe_constraints.must_preserve == []
    assert analysis.content_complexity.dense_details is False
    assert analysis.composition.foreground == []
    assert analysis.composition.attention_regions == []
    assert analysis.raw_model_output is None


def test_missing_fields_generate_structured_warnings():
    analysis = analysis_from_model_output('{"summary":"minimal"}')
    assert analysis.summary == "minimal"
    assert analysis.validation_warnings
    assert all(w.code and w.field and w.message for w in analysis.validation_warnings)


def test_spatial_fields_validate_with_defaults():
    analysis = ImageAnalysis.model_validate(
        {
            "subjects": [
                {
                    "label": "lake",
                    "spatial": {
                        "region": "center",
                        "distance_layer": "midground",
                        "relative_size": "large",
                        "confidence": 1.4,
                    },
                }
            ],
            "composition": {
                "foreground": ["grass"],
                "midground": ["lake"],
                "background": ["snow-covered hills"],
                "attention_regions": [
                    {
                        "label": "lake and hills",
                        "region": "center",
                        "importance": "primary",
                        "confidence": 0.9,
                    }
                ],
            },
        }
    )
    assert analysis.subjects[0].spatial.region == "center"
    assert analysis.subjects[0].spatial.confidence == 1.0
    assert analysis.composition.attention_regions[0].region == "center"


def test_new_signal_fields_validate():
    analysis = ImageAnalysis.model_validate(
        {
            "image_metadata": {"width": 1920, "height": 1080, "orientation": "landscape", "aspect_ratio": 1.7778},
            "spatial_map": {
                "primary_regions": [
                    {
                        "label": "lake",
                        "box_normalized": {"x": -1, "y": 0.35, "w": 2, "h": 0.3},
                        "center": {"x": 0.5, "y": 0.5},
                        "importance": "primary",
                        "edge_margin": "safe",
                        "preserve_for_reframe": True,
                    }
                ],
                "important_regions_span": "wide",
                "safe_reframe_difficulty": "medium",
            },
            "dynamic_potential": {
                "level": "medium",
                "natural_motion_elements": ["clouds", "water"],
                "camera_motion_affordances": ["slow lateral pan"],
                "motion_risks": [],
            },
            "reframe_constraints": {
                "must_preserve": ["lake"],
                "avoid_cutting": [],
                "wide_composition": True,
                "vertical_crop_risk": "high",
            },
            "content_complexity": {"level": "low"},
        }
    )
    assert analysis.image_metadata.orientation == "landscape"
    assert analysis.spatial_map.primary_regions[0].box_normalized.x == 0.0
    assert analysis.spatial_map.primary_regions[0].box_normalized.w == 1.0
    assert analysis.reframe_constraints.vertical_crop_risk == "high"
