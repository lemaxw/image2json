from __future__ import annotations

from typing import Any

from image2json.models import SCHEMA_VERSION, ValidationWarning

EXPECTED_TOP_LEVEL_FIELDS = [
    "schema_version",
    "image_metadata",
    "summary",
    "detailed_description",
    "subjects",
    "scene",
    "style",
    "composition",
    "visual_quality",
    "text",
    "people",
    "objects",
    "spatial_map",
    "dynamic_potential",
    "soundscape",
    "reframe_constraints",
    "content_complexity",
    "framing_risks",
    "generation_risks",
    "confidence",
    "uncertainties",
    "raw_model_output",
    "validation_warnings",
]


def generate_validation_warnings(data: dict[str, Any]) -> list[ValidationWarning]:
    warnings: list[ValidationWarning] = []
    for field in EXPECTED_TOP_LEVEL_FIELDS:
        if field in {"raw_model_output", "validation_warnings"}:
            continue
        if field not in data:
            warnings.append(
                ValidationWarning(
                    code="missing_field",
                    field=field,
                    message=f"Model output did not include '{field}'; a safe default was used.",
                )
            )
        elif data[field] is None:
            warnings.append(
                ValidationWarning(
                    code="null_field",
                    field=field,
                    message=f"Model output set '{field}' to null; a safe default may have been used.",
                )
            )

    if data.get("schema_version") not in {None, SCHEMA_VERSION}:
        warnings.append(
            ValidationWarning(
                code="schema_version_mismatch",
                field="schema_version",
                message=f"Expected schema_version '{SCHEMA_VERSION}', got {data.get('schema_version')!r}.",
            )
        )

    confidence = data.get("confidence")
    if isinstance(confidence, dict):
        overall = confidence.get("overall")
        if isinstance(overall, (int, float)) and not 0.0 <= float(overall) <= 1.0:
            warnings.append(
                ValidationWarning(
                    code="confidence_out_of_range",
                    field="confidence.overall",
                    message="Confidence was outside 0.0-1.0 and was clamped.",
                )
            )
    elif confidence is not None:
        warnings.append(
            ValidationWarning(
                code="malformed_field",
                field="confidence",
                message="Expected confidence to be an object; a safe default was used.",
            )
        )

    return warnings
