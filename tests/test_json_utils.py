import json

from image2json.json_utils import analysis_from_model_output, extract_json_object


def test_extract_plain_json_object():
    data = extract_json_object('{"schema_version":"1.0","summary":"a scene"}')
    assert data["summary"] == "a scene"


def test_extract_markdown_wrapped_json():
    data = extract_json_object('Here:\n```json\n{"summary":"wrapped"}\n```')
    assert data["summary"] == "wrapped"


def test_extract_best_object_from_explanatory_text():
    raw = 'noise {"foo": true} then {"schema_version":"1.0","summary":"best","subjects":[]}'
    data = extract_json_object(raw)
    assert data["summary"] == "best"


def test_analysis_from_invalid_output_uses_safe_defaults():
    analysis = analysis_from_model_output("not json at all")
    assert analysis.schema_version == "1.0"
    assert analysis.summary == ""
    assert any(w.code == "json_extraction_failed" for w in analysis.validation_warnings)


def test_dumped_analysis_is_json_serializable():
    analysis = analysis_from_model_output(json.dumps({"summary": "ok", "confidence": {"overall": 2.0}}))
    payload = analysis.model_dump(mode="json")
    assert payload["confidence"]["overall"] == 1.0
    assert any(w.code == "confidence_out_of_range" for w in analysis.validation_warnings)


def test_derives_subjects_and_attention_regions_from_focal_points():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "summary": "landscape",
                "composition": {
                    "focal_points": ["lake", "snow-covered hills"],
                    "foreground": ["grass"],
                    "midground": ["lake"],
                    "background": ["snow-covered hills", "sky"],
                    "edge_content": ["snow-covered hills on left and right"],
                },
            }
        )
    )
    assert [subject.label for subject in analysis.subjects] == ["lake", "snow-covered hills"]
    assert analysis.subjects[0].spatial.distance_layer == "midground"
    assert analysis.subjects[1].spatial.distance_layer == "background"
    assert analysis.composition.attention_regions[0].label == "lake"
    assert analysis.spatial_map.primary_regions[0].label == "lake"
    assert analysis.reframe_constraints.must_preserve == ["lake", "snow-covered hills"]
    assert "water" in analysis.dynamic_potential.natural_motion_elements
    assert any(w.field == "composition.attention_regions" for w in analysis.validation_warnings)


def test_many_matching_edges_becomes_near_edge_not_touching_all_edges():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "composition": {
                    "focal_points": ["city skyline"],
                    "midground": ["city skyline"],
                    "edge_content": ["city skyline near top, left, right, and bottom edges"],
                },
            }
        )
    )
    assert analysis.spatial_map.primary_regions[0].edge_margin == "near_edge"


def test_injects_image_metadata_and_normalizes_labels_and_text():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "image_metadata": {"width": 1920, "height": 1080, "orientation": "landscape", "aspect_ratio": 1.7778},
                "subjects": [{"description": "central mountain lake"}],
                "objects": [{"location": "bottom edge"}],
                "people": [{"description": "visitor near display"}],
                "text": {"has_visible_text": True, "items": []},
                "composition": {"focal_points": ["lake"], "depth": "deep"},
            }
        ),
        image_metadata={"width": 1200, "height": 800, "orientation": "landscape", "aspect_ratio": 1.5},
    )
    assert analysis.image_metadata.width == 1200
    assert any(w.code == "model_metadata_overridden" for w in analysis.validation_warnings)
    assert analysis.subjects[0].label == "central mountain lake"
    assert analysis.objects[0].label == "bottom edge"
    assert analysis.people[0].label == "visitor near display"
    assert analysis.text.items == []
    assert analysis.text.text_regions[0].preserve_for_reframe is True
    assert analysis.reframe_constraints.wide_composition is False
    assert analysis.reframe_constraints.vertical_crop_risk == "high"
    assert analysis.content_complexity.readable_text is True
    assert any(w.code == "missing_text_items" for w in analysis.validation_warnings)


def test_lighting_does_not_become_natural_motion_element():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "style": {"lighting": "bright natural light"},
                "composition": {"focal_points": ["lake"], "midground": ["lake"]},
            }
        )
    )
    assert "lights" not in analysis.dynamic_potential.natural_motion_elements
    assert "water" in analysis.dynamic_potential.natural_motion_elements


def test_normalizes_primary_region_edge_margin_from_box():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "spatial_map": {
                    "primary_regions": [
                        {
                            "label": "photo grid",
                            "box_normalized": {"x": 0.15, "y": 0.02, "w": 0.85, "h": 0.98},
                            "center": {"x": 0.5, "y": 0.5},
                            "importance": "primary",
                            "edge_margin": "safe",
                            "preserve_for_reframe": True,
                        }
                    ]
                }
            }
        )
    )
    assert analysis.spatial_map.primary_regions[0].edge_margin == "touching_edge"


def test_full_width_important_content_is_separate_from_wide_composition():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "spatial_map": {
                    "primary_regions": [
                        {
                            "label": "photo grid",
                            "box_normalized": {"x": 0.0, "y": 0.1, "w": 1.0, "h": 0.7},
                            "center": {"x": 0.5, "y": 0.45},
                            "importance": "primary",
                            "edge_margin": "near_edge",
                            "preserve_for_reframe": True,
                        }
                    ],
                    "important_regions_span": "full_width",
                },
                "reframe_constraints": {"wide_composition": False},
            }
        ),
        image_metadata={"width": 4080, "height": 3060, "orientation": "landscape", "aspect_ratio": 1.3333},
    )
    assert analysis.reframe_constraints.wide_composition is False
    assert analysis.reframe_constraints.full_width_important_content is True


def test_primary_region_center_is_derived_from_model_box():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "spatial_map": {
                    "primary_regions": [
                        {
                            "label": "stream",
                            "box_normalized": {"x": 0.4, "y": 0.5, "w": 0.3, "h": 0.4},
                            "importance": "primary",
                            "edge_margin": "safe",
                            "preserve_for_reframe": True,
                        }
                    ]
                }
            }
        )
    )
    assert analysis.spatial_map.primary_regions[0].center.model_dump() == {"x": 0.55, "y": 0.7}


def test_dynamic_inference_warning_message_is_clear():
    analysis = analysis_from_model_output(
        json.dumps({"composition": {"foreground": ["grass"], "midground": ["lake"], "background": ["clouds"]}})
    )
    messages = [warning.message for warning in analysis.validation_warnings if warning.field == "dynamic_potential.cues"]
    assert messages == ["Dynamic potential was inferred from composition, depth, or visible physical elements."]


def test_avoid_sounds_do_not_create_visible_motion_elements():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "summary": "Ancient temple under clouds",
                "soundscape": {"avoid_sounds": ["water", "traffic"]},
            }
        )
    )
    assert "clouds" in analysis.dynamic_potential.natural_motion_elements
    assert "water" not in analysis.dynamic_potential.natural_motion_elements


def test_source_aspect_ratio_takes_priority_for_wide_composition():
    analysis = analysis_from_model_output(
        json.dumps({"composition": {"layout": "wide horizontal"}}),
        image_metadata={"width": 6000, "height": 4000, "orientation": "landscape", "aspect_ratio": 1.5},
    )
    assert analysis.reframe_constraints.wide_composition is False


def test_watermark_does_not_imply_visible_water_motion():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "summary": "Ancient temple",
                "text": {
                    "has_visible_text": True,
                    "items": [{"content": "Maxim Pshater"}],
                    "text_regions": [{"label": "photographer watermark"}],
                },
            }
        )
    )
    assert "water" not in analysis.dynamic_potential.natural_motion_elements


def test_unsupported_model_motion_category_is_removed():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "summary": "Dry stone temple under clouds",
                "dynamic_potential": {"natural_motion_elements": ["water", "clouds"]},
            }
        )
    )
    assert "water" not in analysis.dynamic_potential.natural_motion_elements
    assert "clouds" in analysis.dynamic_potential.natural_motion_elements


def test_camera_affordance_cannot_introduce_absent_scene_type():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "summary": "Ancient temple on rocky terrain",
                "composition": {"depth": "deep"},
                "dynamic_potential": {"camera_motion_affordances": ["gentle push into the valley"]},
            }
        )
    )
    assert "gentle push into the valley" not in analysis.dynamic_potential.camera_motion_affordances
    assert "gentle push-in" in analysis.dynamic_potential.camera_motion_affordances


def test_empty_and_null_text_items_are_removed():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "text": {
                    "has_visible_text": True,
                    "items": [{"content": ""}, {"content": "null"}, {"content": "© Author"}],
                    "text_regions": [{"label": "empty text region"}, {"label": "watermark"}],
                }
            }
        )
    )
    assert [item.content for item in analysis.text.items] == ["© Author"]
    assert [region.label for region in analysis.text.text_regions] == ["watermark"]


def test_unreadable_region_cannot_have_invented_ocr_content():
    analysis = analysis_from_model_output(
        json.dumps(
            {
                "text": {
                    "has_visible_text": True,
                    "items": [{"content": "Scaffolding"}],
                    "text_regions": [{"label": "possible marks", "readability": "unreadable"}],
                }
            }
        )
    )
    assert analysis.text.items == []
