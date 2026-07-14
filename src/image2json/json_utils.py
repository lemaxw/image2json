from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from image2json.models import ImageAnalysis, ValidationWarning
from image2json.warnings import EXPECTED_TOP_LEVEL_FIELDS, generate_validation_warnings

FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


class JsonExtractionError(ValueError):
    """Raised when model output does not contain a valid JSON object."""


def _balanced_object_candidates(text: str) -> Iterable[str]:
    starts = [index for index, char in enumerate(text) if char == "{"]
    for start in starts:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield text[start : index + 1]
                    break


def _candidate_strings(text: str) -> list[str]:
    candidates = [text.strip()]
    candidates.extend(match.group(1).strip() for match in FENCED_JSON_RE.finditer(text))
    candidates.extend(_balanced_object_candidates(text))
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _score_object(value: dict[str, Any]) -> tuple[int, int]:
    expected_matches = sum(1 for field in EXPECTED_TOP_LEVEL_FIELDS if field in value)
    return expected_matches, len(value)


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract the most likely JSON object from model output."""
    best: dict[str, Any] | None = None
    best_score = (-1, -1)
    for candidate in _candidate_strings(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        score = _score_object(parsed)
        if score > best_score:
            best = parsed
            best_score = score
    if best is None:
        raise JsonExtractionError("Model output did not contain a valid JSON object.")
    return best


MOTION_KEYWORDS = {
    "cloud": "clouds",
    "water": "water",
    "lake": "water",
    "river": "water",
    "sea": "water",
    "ocean": "water",
    "wave": "water",
    "foliage": "foliage",
    "tree": "foliage",
    "grass": "foliage",
    "crowd": "crowds",
    "vehicle": "vehicles",
    "car": "vehicles",
    "fabric": "fabric",
    "smoke": "smoke",
    "reflection": "reflections",
}


def analysis_from_model_output(
    raw_output: str,
    image_metadata: dict[str, Any] | None = None,
) -> ImageAnalysis:
    warnings: list[ValidationWarning] = []
    try:
        data = extract_json_object(raw_output)
    except JsonExtractionError:
        data = {}
        warnings.append(
            ValidationWarning(
                code="json_extraction_failed",
                field="raw_model_output",
                message="Could not extract a valid JSON object from model output; safe defaults were used.",
                severity="error",
            )
        )

    if image_metadata:
        existing_metadata = data.get("image_metadata")
        if isinstance(existing_metadata, dict) and _metadata_differs(existing_metadata, image_metadata):
            warnings.append(
                ValidationWarning(
                    code="model_metadata_overridden",
                    field="image_metadata",
                    message="Model-provided image metadata was overridden with source file metadata.",
                )
            )
        data["image_metadata"] = image_metadata
    warnings.extend(_normalize_required_labels(data))
    warnings.extend(_normalize_text_items(data))
    warnings.extend(_derive_spatial_fields(data))
    warnings.extend(_normalize_motion_and_constraints(data))
    warnings.extend(generate_validation_warnings(data))
    data["raw_model_output"] = raw_output
    existing_warnings = data.get("validation_warnings")
    if isinstance(existing_warnings, list):
        warnings.extend(
            item if isinstance(item, ValidationWarning) else ValidationWarning.model_validate(item)
            for item in existing_warnings
            if isinstance(item, (dict, ValidationWarning))
        )
    data["validation_warnings"] = warnings

    try:
        return ImageAnalysis.model_validate(data)
    except ValidationError as exc:
        fallback = ImageAnalysis(raw_model_output=raw_output)
        fallback.validation_warnings = warnings + [
            ValidationWarning(
                code="validation_failed",
                field="root",
                message=str(exc),
                severity="error",
            )
        ]
        return fallback


def dump_analysis(analysis: ImageAnalysis, *, include_raw: bool, pretty: bool) -> str:
    payload = analysis.model_dump(mode="json")
    if not include_raw:
        payload["raw_model_output"] = None
    return json.dumps(payload, indent=2 if pretty else None, sort_keys=pretty)


def _metadata_differs(model_metadata: dict[str, Any], source_metadata: dict[str, Any]) -> bool:
    for key in ("width", "height", "orientation"):
        if model_metadata.get(key) not in {None, "", source_metadata.get(key)}:
            return True
    model_ratio = model_metadata.get("aspect_ratio")
    source_ratio = source_metadata.get("aspect_ratio")
    if isinstance(model_ratio, (int, float)) and isinstance(source_ratio, (int, float)):
        return abs(float(model_ratio) - float(source_ratio)) > 0.01
    return False


def _normalize_required_labels(data: dict[str, Any]) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []
    for collection_name, fallback in (("subjects", "subject"), ("objects", "object"), ("people", "person")):
        items = data.get(collection_name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            if isinstance(label, str) and label.strip():
                item["label"] = label.strip()
                continue
            derived = _first_nonempty_string(item.get("description"), item.get("apparent_activity"), item.get("location"))
            item["label"] = _short_label(derived) if derived else fallback
            warnings.append(
                ValidationWarning(
                    code="derived_field",
                    field=f"{collection_name}.{index}.label",
                    message=f"A non-empty label was derived for {collection_name}[{index}].",
                )
            )
    return warnings


def _normalize_text_items(data: dict[str, Any]) -> list[ValidationWarning]:
    text = data.get("text")
    if not isinstance(text, dict) or text.get("has_visible_text") is not True:
        return []
    items = text.get("items")
    warnings: list[ValidationWarning] = []
    if not isinstance(items, list) or not items:
        text.setdefault("text_regions", [_fallback_text_region(data)])
        return [
            ValidationWarning(
                code="missing_text_items",
                field="text.items",
                message="Visible text was reported but no text items were provided.",
            )
        ]
    regions = text.get("text_regions")
    text["items"] = [
        item
        for index, item in enumerate(items)
        if isinstance(item, dict)
        and str(item.get("content") or "").strip().lower() not in {"", "null", "none"}
        and not (
            isinstance(regions, list)
            and index < len(regions)
            and isinstance(regions[index], dict)
            and regions[index].get("readability") == "unreadable"
        )
    ]
    items = text["items"]
    if isinstance(regions, list):
        object_labels = {
            str(item.get("label") or "").strip().lower()
            for collection in (data.get("subjects"), data.get("objects"))
            if isinstance(collection, list)
            for item in collection
            if isinstance(item, dict)
        }
        text["text_regions"] = [
            region
            for region in regions
            if not isinstance(region, dict)
            or str(region.get("label") or "").strip().lower()
            not in {"", "null", "none", "unknown text", "empty text region"}
            and not (
                region.get("readability") == "unreadable"
                and str(region.get("label") or "").strip().lower().removesuffix(" text") in object_labels
            )
        ]
        if "graffiti" in str(text.get("notes") or "").lower():
            for region in text["text_regions"]:
                if isinstance(region, dict) and region.get("label") == "visible labels on photos":
                    region["label"] = "graffiti text"
                    region["location"] = "center"
    if not items and not text.get("text_regions"):
        text["text_regions"] = [_fallback_text_region(data)]
    for index, item in enumerate(items):
        if isinstance(item, dict) and not str(item.get("content") or "").strip():
            warnings.append(
                ValidationWarning(
                    code="missing_text_content",
                    field=f"text.items.{index}.content",
                    message="Visible text item did not include readable content.",
                )
            )
    if not text.get("text_regions"):
        text["text_regions"] = [_text_region_from_item(item) for item in items if isinstance(item, dict)]
    return warnings


def _fallback_text_region(data: dict[str, Any]) -> dict[str, Any]:
    label = "visible text"
    text_blob = " ".join(_flatten_strings(data))
    if "graffiti" in text_blob.lower():
        label = "graffiti text"
    elif "watermark" in text_blob.lower() or "signature" in text_blob.lower():
        label = "photographer watermark"
    elif "label" in text_blob.lower() or "panel" in text_blob.lower() or "photo" in text_blob.lower():
        label = "visible labels on photos"
    return {
        "label": label,
        "box_normalized": None,
        "location": _location_from_text(data),
        "readability": "partial",
        "preserve_for_reframe": True,
    }


def _text_region_from_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(item.get("content") or "visible text"),
        "box_normalized": None,
        "location": str(item.get("location") or ""),
        "readability": "readable" if str(item.get("content") or "").strip() else "partial",
        "preserve_for_reframe": True,
    }


def _location_from_text(data: dict[str, Any]) -> str:
    text = data.get("text")
    if isinstance(text, dict) and isinstance(text.get("notes"), str) and text["notes"].strip():
        notes = text["notes"].strip()
        if "graffiti" in notes.lower():
            return "center"
        return notes
    return "unknown"


def _derive_spatial_fields(data: dict[str, Any]) -> list[ValidationWarning]:
    """Derive minimal spatial helpers from model-provided composition evidence."""
    warnings: list[ValidationWarning] = []
    composition = data.get("composition")
    if not isinstance(composition, dict):
        return warnings

    focal_points = composition.get("focal_points")
    if not isinstance(focal_points, list):
        return warnings
    labels = [item for item in focal_points if isinstance(item, str) and item.strip()]
    if not labels:
        return warnings

    if not data.get("subjects"):
        data["subjects"] = [
            {
                "label": label,
                "description": "",
                "prominence": "primary" if index == 0 else "supporting",
                "spatial": _spatial_from_composition(label, composition),
                "confidence": None,
            }
            for index, label in enumerate(labels)
        ]
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="subjects",
                message="Subjects were derived from composition.focal_points because the model left subjects empty.",
            )
        )
    else:
        subjects = data.get("subjects")
        if isinstance(subjects, list):
            for subject in subjects:
                if not isinstance(subject, dict) or not isinstance(subject.get("label"), str):
                    continue
                spatial = subject.get("spatial")
                if isinstance(spatial, dict) and any(spatial.get(key) for key in ("region", "distance_layer", "relative_size", "touches_edges")):
                    continue
                subject["spatial"] = _spatial_from_composition(subject["label"], composition)

    if not composition.get("attention_regions"):
        composition["attention_regions"] = [
            {
                "label": label,
                "description": "",
                "region": _region_from_spatial(_spatial_from_composition(label, composition)),
                "importance": "primary" if index == 0 else "supporting",
                "reason": "Derived from composition.focal_points.",
                "confidence": None,
            }
            for index, label in enumerate(labels[:5])
        ]
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="composition.attention_regions",
                message=(
                    "Attention regions were derived from composition.focal_points because the model "
                    "left attention_regions empty."
                ),
            )
        )

    spatial_map = data.get("spatial_map")
    if not isinstance(spatial_map, dict):
        spatial_map = {}
        data["spatial_map"] = spatial_map
    if not spatial_map.get("primary_regions"):
        spatial_map["primary_regions"] = [
            {
                "label": label,
                "box_normalized": _box_from_spatial(_spatial_from_composition(label, composition)),
                "center": _center_from_box(_box_from_spatial(_spatial_from_composition(label, composition))),
                "importance": "primary" if index == 0 else "supporting",
                "edge_margin": _edge_margin(_matching_edges(label, composition)),
                "preserve_for_reframe": True,
            }
            for index, label in enumerate(labels[:5])
        ]
        spatial_map.setdefault("important_regions_span", _infer_region_span(spatial_map["primary_regions"]))
        spatial_map.setdefault("safe_reframe_difficulty", "")
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="spatial_map.primary_regions",
                message="Primary spatial regions were derived from composition.focal_points.",
            )
        )

    return warnings


def _spatial_from_composition(label: str, composition: dict[str, Any]) -> dict[str, Any]:
    distance_layer = _matching_layer(label, composition)
    return {
        "region": distance_layer or "",
        "x_position": None,
        "y_position": None,
        "distance_layer": distance_layer,
        "relative_size": None,
        "touches_edges": _matching_edges(label, composition),
        "occluded": None,
        "notes": "Derived from composition fields.",
        "confidence": None,
    }


def _matching_layer(label: str, composition: dict[str, Any]) -> str | None:
    normalized = label.lower()
    for layer in ("foreground", "midground", "background"):
        values = composition.get(layer)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and (normalized in value.lower() or value.lower() in normalized):
                return layer
    return None


def _matching_edges(label: str, composition: dict[str, Any]) -> list[str]:
    normalized = label.lower()
    edges: set[str] = set()
    edge_content = composition.get("edge_content")
    if not isinstance(edge_content, list):
        return []
    for value in edge_content:
        if not isinstance(value, str) or normalized not in value.lower():
            continue
        lowered = value.lower()
        for edge in ("top", "right", "bottom", "left"):
            if edge in lowered:
                edges.add(edge)
    return sorted(edges)


def _region_from_spatial(spatial: dict[str, Any]) -> str:
    region = spatial.get("region")
    if isinstance(region, str) and region:
        return region
    return "unspecified"


def _normalize_motion_and_constraints(data: dict[str, Any]) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []
    visible_text = bool(isinstance(data.get("text"), dict) and data["text"].get("has_visible_text"))
    text_blob = " ".join(_flatten_strings(data))
    visible_evidence_blob = " ".join(
        item
        for field in (
            "summary",
            "detailed_description",
            "subjects",
            "scene",
            "composition",
            "objects",
            "people",
            "text",
        )
        for item in _flatten_strings(data.get(field))
    )
    motion_elements = _motion_elements_from_text(visible_evidence_blob)

    dynamic = data.get("dynamic_potential")
    if not isinstance(dynamic, dict):
        dynamic = {}
        data["dynamic_potential"] = dynamic
    cues = dynamic.get("cues")
    if not isinstance(cues, list):
        cues = []
    existing_elements = dynamic.get("natural_motion_elements")
    if not isinstance(existing_elements, list):
        existing_elements = []
    evidence_categories = {item.lower() for item in motion_elements}
    canonical_categories = {item.lower() for item in MOTION_KEYWORDS.values()}
    existing_elements = [
        item
        for item in existing_elements
        if item.lower() not in canonical_categories or item.lower() in evidence_categories
    ]
    merged_elements = _dedupe_strings(
        item
        for item in [*existing_elements, *motion_elements]
        if item.strip().lower() not in {"none", "no motion", "no visible motion"}
    )
    if _has_depth_layers(data):
        merged_elements = _dedupe_strings([*merged_elements, "depth layers"])
    dynamic["natural_motion_elements"] = merged_elements
    if not cues and merged_elements:
        dynamic["cues"] = merged_elements
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="dynamic_potential.cues",
                message="Dynamic potential was inferred from composition, depth, or visible physical elements.",
            )
        )
    if not dynamic.get("camera_motion_affordances"):
        dynamic["camera_motion_affordances"] = _camera_affordances(data, merged_elements)
    else:
        dynamic["camera_motion_affordances"] = _supported_camera_affordances(
            dynamic["camera_motion_affordances"], visible_evidence_blob
        ) or _camera_affordances(data, merged_elements)
    if not dynamic.get("motion_risks"):
        dynamic["motion_risks"] = _motion_risks(data, visible_text)
    if merged_elements and dynamic.get("level") in {"", None, "none"}:
        dynamic["level"] = "low"
    elif not dynamic.get("level"):
        dynamic["level"] = "medium" if merged_elements else "none"

    complexity = data.get("content_complexity")
    if not isinstance(complexity, dict):
        complexity = {}
        data["content_complexity"] = complexity
    if visible_text and complexity.get("readable_text") is not True:
        complexity["readable_text"] = True
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="content_complexity.readable_text",
                message="Readable text complexity was inferred because text.has_visible_text is true.",
            )
        )
    else:
        complexity.setdefault("readable_text", visible_text)
    complexity.setdefault("faces", bool(data.get("people")))
    complexity.setdefault("dense_details", _contains_any(text_blob, ["grid", "panorama", "crowd", "exhibition", "many", "dense"]))
    complexity.setdefault("fine_geometry", _contains_any(text_blob, ["building", "city", "architecture", "text", "grid", "panel"]))
    complexity.setdefault("repeating_patterns", _contains_any(text_blob, ["grid", "windows", "panels", "pattern", "repeating"]))
    complexity.setdefault("hands", _contains_any(text_blob, ["hand", "hands"]))
    if not complexity.get("level"):
        flags = sum(1 for key in ("dense_details", "faces", "hands", "readable_text", "repeating_patterns", "fine_geometry") if complexity.get(key))
        complexity["level"] = "high" if flags >= 3 else "medium" if flags >= 1 else "low"

    reframe = data.get("reframe_constraints")
    if not isinstance(reframe, dict):
        reframe = {}
        data["reframe_constraints"] = reframe
    labels = _important_labels(data)
    if not reframe.get("must_preserve"):
        reframe["must_preserve"] = labels
    if not reframe.get("avoid_cutting"):
        reframe["avoid_cutting"] = _avoid_cutting_labels(data)
    inferred_wide = _is_wide_composition(data)
    if inferred_wide and reframe.get("wide_composition") is not True:
        reframe["wide_composition"] = True
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="reframe_constraints.wide_composition",
                message="Wide composition was inferred from source metadata or composition evidence.",
            )
        )
    else:
        reframe.setdefault("wide_composition", inferred_wide)
    inferred_vertical_risk = _vertical_crop_risk(data, bool(reframe["wide_composition"]), complexity)
    if _risk_rank(inferred_vertical_risk) > _risk_rank(str(reframe.get("vertical_crop_risk") or "")):
        reframe["vertical_crop_risk"] = inferred_vertical_risk
        warnings.append(
            ValidationWarning(
                code="derived_field",
                field="reframe_constraints.vertical_crop_risk",
                message="Vertical reframe risk was raised from generic metadata and complexity signals.",
            )
        )
    else:
        reframe.setdefault("vertical_crop_risk", inferred_vertical_risk)
    reframe.setdefault("reason", "")

    spatial_map = data.get("spatial_map")
    if isinstance(spatial_map, dict):
        _normalize_primary_region_edge_margins(spatial_map)
        if not spatial_map.get("important_regions_span"):
            spatial_map["important_regions_span"] = _infer_region_span(spatial_map.get("primary_regions", []))
        full_width_important_content = spatial_map.get("important_regions_span") == "full_width"
        if full_width_important_content and reframe.get("full_width_important_content") is not True:
            reframe["full_width_important_content"] = True
            warnings.append(
                ValidationWarning(
                    code="derived_field",
                    field="reframe_constraints.full_width_important_content",
                    message="Important content appears to span the full source width.",
                )
            )
        else:
            reframe.setdefault("full_width_important_content", bool(full_width_important_content))
        inferred_difficulty = _safe_reframe_difficulty(reframe, complexity)
        if _risk_rank(inferred_difficulty) > _risk_rank(str(spatial_map.get("safe_reframe_difficulty") or "")):
            spatial_map["safe_reframe_difficulty"] = inferred_difficulty
        else:
            spatial_map.setdefault("safe_reframe_difficulty", inferred_difficulty)

    return warnings


def _box_from_spatial(spatial: dict[str, Any]) -> dict[str, float]:
    region = str(spatial.get("region") or "").lower()
    layer = str(spatial.get("distance_layer") or "").lower()
    if region in {"foreground", "midground", "background"}:
        layer = region
    if layer == "foreground":
        return {"x": 0.0, "y": 0.6, "w": 1.0, "h": 0.4}
    if layer == "background":
        return {"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.4}
    if layer == "midground":
        return {"x": 0.1, "y": 0.3, "w": 0.8, "h": 0.4}
    return {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}


def _center_from_box(box: dict[str, float]) -> dict[str, float]:
    return {"x": round(box["x"] + box["w"] / 2, 4), "y": round(box["y"] + box["h"] / 2, 4)}


def _edge_margin(edges: list[str]) -> str:
    if len(set(edges)) >= 3:
        return "near_edge"
    if edges:
        return "touching_edge"
    return "safe"


def _infer_region_span(regions: Any) -> str:
    if not isinstance(regions, list) or not regions:
        return ""
    widths = []
    for region in regions:
        if isinstance(region, dict):
            box = region.get("box_normalized")
            if isinstance(box, dict):
                widths.append(float(box.get("w") or 0.0))
    if not widths:
        return ""
    widest = max(widths)
    if widest >= 0.9:
        return "full_width"
    if widest >= 0.65:
        return "wide"
    if widest >= 0.35:
        return "moderate"
    return "narrow"


def _safe_reframe_difficulty(reframe: dict[str, Any], complexity: dict[str, Any]) -> str:
    if reframe.get("vertical_crop_risk") == "high" or complexity.get("level") == "high":
        return "high"
    if reframe.get("vertical_crop_risk") == "medium" or complexity.get("level") == "medium":
        return "medium"
    return "low"


def _risk_rank(value: str) -> int:
    return {"": 0, "none": 0, "low": 1, "medium": 2, "high": 3}.get(value, 0)


def _normalize_primary_region_edge_margins(spatial_map: dict[str, Any]) -> None:
    regions = spatial_map.get("primary_regions")
    if not isinstance(regions, list):
        return
    for region in regions:
        if not isinstance(region, dict):
            continue
        box = region.get("box_normalized")
        if not isinstance(box, dict):
            continue
        region["center"] = _center_from_box(
            {key: float(box.get(key) or 0.0) for key in ("x", "y", "w", "h")}
        )
        inferred = _edge_margin_from_box(box)
        if _edge_margin_rank(inferred) > _edge_margin_rank(str(region.get("edge_margin") or "")):
            region["edge_margin"] = inferred


def _edge_margin_from_box(box: dict[str, Any]) -> str:
    x = float(box.get("x") or 0.0)
    y = float(box.get("y") or 0.0)
    w = float(box.get("w") or 0.0)
    h = float(box.get("h") or 0.0)
    touches = x <= 0.0 or y <= 0.0 or x + w >= 1.0 or y + h >= 1.0
    near = x <= 0.05 or y <= 0.05 or x + w >= 0.95 or y + h >= 0.95
    if touches:
        return "touching_edge"
    if near:
        return "near_edge"
    return "safe"


def _edge_margin_rank(value: str) -> int:
    return {"": 0, "safe": 1, "near_edge": 2, "touching_edge": 3}.get(value, 0)


def _vertical_crop_risk(data: dict[str, Any], wide: bool, complexity: dict[str, Any]) -> str:
    if wide or complexity.get("readable_text") or complexity.get("dense_details"):
        return "high"
    if data.get("people") or complexity.get("fine_geometry"):
        return "medium"
    return "low"


def _is_wide_composition(data: dict[str, Any]) -> bool:
    metadata = data.get("image_metadata")
    if isinstance(metadata, dict) and float(metadata.get("aspect_ratio") or 0.0) > 0.0:
        return metadata.get("orientation") == "landscape" and float(metadata.get("aspect_ratio") or 0.0) >= 1.7
    composition = data.get("composition")
    if isinstance(composition, dict):
        text = " ".join(str(composition.get(key) or "") for key in ("layout", "visual_balance", "negative_space")).lower()
        return any(word in text for word in ("wide", "panorama", "horizontal"))
    return False


def _has_depth_layers(data: dict[str, Any]) -> bool:
    composition = data.get("composition")
    if not isinstance(composition, dict):
        return False
    if composition.get("depth") not in {"", None, "flat", "none"}:
        return True
    return any(composition.get(layer) for layer in ("foreground", "midground", "background"))


def _important_labels(data: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for collection_name in ("subjects", "objects", "people"):
        items = data.get(collection_name)
        if isinstance(items, list):
            labels.extend(str(item.get("label")) for item in items if isinstance(item, dict) and item.get("label"))
    composition = data.get("composition")
    if isinstance(composition, dict) and isinstance(composition.get("focal_points"), list):
        labels.extend(str(item) for item in composition["focal_points"] if isinstance(item, str))
    return _dedupe_strings(labels)


def _avoid_cutting_labels(data: dict[str, Any]) -> list[str]:
    labels = []
    for region in data.get("spatial_map", {}).get("primary_regions", []) if isinstance(data.get("spatial_map"), dict) else []:
        if isinstance(region, dict) and region.get("edge_margin") in {"near_edge", "touching_edge"}:
            labels.append(str(region.get("label") or "important edge content"))
    text = data.get("text")
    if isinstance(text, dict) and text.get("has_visible_text"):
        labels.append("visible text")
    return _dedupe_strings(labels)


def _camera_affordances(data: dict[str, Any], elements: list[str]) -> list[str]:
    affordances: list[str] = []
    if elements:
        affordances.append("subtle atmospheric motion")
    composition = data.get("composition")
    if isinstance(composition, dict) and composition.get("depth") not in {"", None, "flat"}:
        affordances.append("gentle push-in")
    if _is_wide_composition(data):
        affordances.append("slow lateral pan")
    return _dedupe_strings(affordances)


def _motion_risks(data: dict[str, Any], visible_text: bool) -> list[str]:
    risks: list[str] = []
    if visible_text:
        risks.append("text distortion")
    if data.get("people"):
        risks.append("face drift")
    text_blob = " ".join(_flatten_strings(data))
    if _contains_any(text_blob, ["building", "architecture", "city", "grid", "panel"]):
        risks.append("geometry wobble")
    return risks


def _motion_elements_from_text(text: str) -> list[str]:
    lowered = text.lower()
    elements = list(
        value
        for key, value in MOTION_KEYWORDS.items()
        if re.search(rf"\b{re.escape(key)}(?:s)?\b", lowered)
    )
    if re.search(r"\bcloudy\b", lowered):
        elements.append("clouds")
    if re.search(r"\bvegetation\b", lowered):
        elements.append("foliage")
    return _dedupe_strings(elements)


def _supported_camera_affordances(affordances: Any, evidence: str) -> list[str]:
    if not isinstance(affordances, list):
        return []
    subject_terms = ("valley", "stream", "road", "water", "building", "temple", "skyline")
    lowered_evidence = evidence.lower()
    return [
        str(item)
        for item in affordances
        if isinstance(item, str)
        and not any(term in item.lower() and term not in lowered_evidence for term in subject_terms)
    ]


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in _flatten_strings(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _flatten_strings(child)]
    return []


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _first_nonempty_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _short_label(value: str) -> str:
    words = value.strip().split()
    return " ".join(words[:4]) if words else ""


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            deduped.append(clean)
    return deduped
