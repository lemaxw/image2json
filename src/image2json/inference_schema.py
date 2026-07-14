from __future__ import annotations

from typing import Any


def _array(item_type: str = "string") -> dict[str, Any]:
    return {"type": "array", "items": {"type": item_type}}


def _object_array(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


SPATIAL = {
    "type": "object",
    "properties": {
        "region": {"type": "string"},
        "distance_layer": {"type": ["string", "null"]},
        "relative_size": {"type": ["string", "null"]},
        "touches_edges": _array(),
        "notes": {"type": "string"},
        "confidence": {"type": ["number", "null"]},
    },
    "required": ["region", "distance_layer", "relative_size", "touches_edges", "notes", "confidence"],
}


MODEL_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "summary": {"type": "string"},
        "detailed_description": {"type": "string"},
        "subjects": _object_array(
            {
                "label": {"type": "string"},
                "description": {"type": "string"},
                "prominence": {"type": ["string", "null"]},
                "spatial": SPATIAL,
                "confidence": {"type": ["number", "null"]},
            },
            ["label", "description", "prominence", "spatial", "confidence"],
        ),
        "scene": {
            "type": "object",
            "properties": {
                "environment": {"type": "string"},
                "location_type": {"type": ["string", "null"]},
                "time_of_day": {"type": ["string", "null"]},
                "weather": {"type": ["string", "null"]},
                "mood": {"type": ["string", "null"]},
            },
            "required": ["environment", "location_type", "time_of_day", "weather", "mood"],
        },
        "style": {
            "type": "object",
            "properties": {
                "medium": {"type": "string"},
                "visual_style": {"type": "string"},
                "color_palette": _array(),
                "lighting": {"type": ["string", "null"]},
            },
            "required": ["medium", "visual_style", "color_palette", "lighting"],
        },
        "composition": {
            "type": "object",
            "properties": {
                "layout": {"type": "string"},
                "depth": {"type": ["string", "null"]},
                "focal_points": _array(),
                "foreground": _array(),
                "midground": _array(),
                "background": _array(),
                "visual_balance": {"type": "string"},
                "edge_content": _array(),
                "attention_regions": _object_array(
                    {
                        "label": {"type": "string"},
                        "description": {"type": "string"},
                        "region": {"type": "string"},
                        "importance": {"type": ["string", "null"]},
                        "reason": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                    },
                    ["label", "description", "region", "importance", "reason", "confidence"],
                ),
            },
            "required": ["layout", "depth", "focal_points", "foreground", "midground", "background", "visual_balance", "edge_content", "attention_regions"],
        },
        "text": {
            "type": "object",
            "properties": {
                "has_visible_text": {"type": "boolean"},
                "items": _object_array(
                    {
                        "content": {"type": "string"},
                        "location": {"type": ["string", "null"]},
                        "confidence": {"type": ["number", "null"]},
                    },
                    ["content", "location", "confidence"],
                ),
                "text_regions": _object_array(
                    {
                        "label": {"type": "string"},
                        "location": {"type": "string"},
                        "readability": {"type": "string", "enum": ["readable", "partial", "unreadable"]},
                        "preserve_for_reframe": {"type": "boolean"},
                    },
                    ["label", "location", "readability", "preserve_for_reframe"],
                ),
                "notes": {"type": "string"},
            },
            "required": ["has_visible_text", "items", "text_regions", "notes"],
        },
        "visual_quality": {
            "type": "object",
            "properties": {
                "overall": {"type": "string"},
                "sharpness": {"type": ["string", "null"]},
                "exposure": {"type": ["string", "null"]},
                "noise": {"type": ["string", "null"]},
                "artifacts": _array(),
                "confidence": {"type": ["number", "null"]},
            },
            "required": ["overall", "sharpness", "exposure", "noise", "artifacts", "confidence"],
        },
        "people": _array("object"),
        "objects": _array("object"),
        "spatial_map": {
            "type": "object",
            "properties": {
                "primary_regions": _object_array(
                    {
                        "label": {"type": "string"},
                        "box_normalized": {
                            "type": "object",
                            "properties": {key: {"type": "number"} for key in ("x", "y", "w", "h")},
                            "required": ["x", "y", "w", "h"],
                        },
                        "importance": {"type": "string", "enum": ["primary", "supporting", "background", "context"]},
                        "edge_margin": {"type": "string", "enum": ["safe", "near_edge", "touching_edge"]},
                        "preserve_for_reframe": {"type": "boolean"},
                    },
                    ["label", "box_normalized", "importance", "edge_margin", "preserve_for_reframe"],
                ),
                "important_regions_span": {"type": "string", "enum": ["narrow", "moderate", "wide", "full_width"]},
                "safe_reframe_difficulty": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["primary_regions", "important_regions_span", "safe_reframe_difficulty"],
        },
        "dynamic_potential": {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "cues": _array(),
                "natural_motion_elements": _array(),
                "camera_motion_affordances": _array(),
                "motion_risks": _array(),
                "notes": {"type": "string"},
            },
            "required": ["level", "cues", "natural_motion_elements", "camera_motion_affordances", "motion_risks", "notes"],
        },
        "soundscape": {
            "type": "object",
            "properties": {
                "environment_type": {"type": "string"},
                "primary_audio_prompt": {"type": "string"},
                "secondary_sounds": _array(),
                "avoid_sounds": _array(),
                "proximity": {"type": "string"},
                "confidence": {"type": ["number", "null"]},
                "reasoning": {"type": "string"},
            },
            "required": ["environment_type", "primary_audio_prompt", "secondary_sounds", "avoid_sounds", "proximity", "confidence", "reasoning"],
        },
        "reframe_constraints": {
            "type": "object",
            "properties": {
                "must_preserve": _array(),
                "avoid_cutting": _array(),
                "wide_composition": {"type": "boolean"},
                "full_width_important_content": {"type": "boolean"},
                "vertical_crop_risk": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["must_preserve", "avoid_cutting", "wide_composition", "full_width_important_content", "vertical_crop_risk", "reason"],
        },
        "content_complexity": {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "dense_details": {"type": "boolean"},
                "faces": {"type": "boolean"},
                "hands": {"type": "boolean"},
                "readable_text": {"type": "boolean"},
                "repeating_patterns": {"type": "boolean"},
                "fine_geometry": {"type": "boolean"},
            },
            "required": ["level", "dense_details", "faces", "hands", "readable_text", "repeating_patterns", "fine_geometry"],
        },
        "framing_risks": _object_array(
            {"type": {"type": "string"}, "description": {"type": "string"}, "severity": {"type": "string"}, "confidence": {"type": ["number", "null"]}},
            ["type", "description", "severity", "confidence"],
        ),
        "generation_risks": _object_array(
            {"type": {"type": "string"}, "description": {"type": "string"}, "severity": {"type": "string"}, "confidence": {"type": ["number", "null"]}},
            ["type", "description", "severity", "confidence"],
        ),
        "confidence": {
            "type": "object",
            "properties": {"overall": {"type": "number"}, "notes": {"type": "string"}},
            "required": ["overall", "notes"],
        },
        "uncertainties": _array(),
    },
    "required": [
        "schema_version", "summary", "detailed_description", "subjects", "scene", "style",
        "composition", "visual_quality", "text", "people", "objects", "spatial_map", "dynamic_potential", "soundscape",
        "reframe_constraints", "content_complexity", "framing_risks", "generation_risks",
        "confidence", "uncertainties",
    ],
}
