from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "1.0"


def _confidence(value: float | int | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


class StableModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ValidationWarning(StableModel):
    code: str
    field: str
    message: str
    severity: str = "warning"


class ImageMetadata(StableModel):
    width: int = 0
    height: int = 0
    orientation: str = ""
    aspect_ratio: float = 0.0


class NormalizedBox(StableModel):
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0

    @field_validator("x", "y", "w", "h", mode="before")
    @classmethod
    def clamp_unit(cls, value: Any) -> float:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, float(value)))


class NormalizedPoint(StableModel):
    x: float = 0.0
    y: float = 0.0

    @field_validator("x", "y", mode="before")
    @classmethod
    def clamp_unit(cls, value: Any) -> float:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, float(value)))


class PrimaryRegion(StableModel):
    label: str = ""
    box_normalized: NormalizedBox = Field(default_factory=NormalizedBox)
    center: NormalizedPoint = Field(default_factory=NormalizedPoint)
    importance: str = ""
    edge_margin: str = ""
    preserve_for_reframe: bool = False


class SpatialMap(StableModel):
    primary_regions: list[PrimaryRegion] = Field(default_factory=list)
    important_regions_span: str = ""
    safe_reframe_difficulty: str = ""


class ReframeConstraints(StableModel):
    must_preserve: list[str] = Field(default_factory=list)
    avoid_cutting: list[str] = Field(default_factory=list)
    wide_composition: bool = False
    full_width_important_content: bool = False
    vertical_crop_risk: str = ""
    reason: str = ""


class ContentComplexity(StableModel):
    level: str = ""
    dense_details: bool = False
    faces: bool = False
    hands: bool = False
    readable_text: bool = False
    repeating_patterns: bool = False
    fine_geometry: bool = False


class SpatialExtent(StableModel):
    region: str = ""
    x_position: str | None = None
    y_position: str | None = None
    distance_layer: str | None = None
    relative_size: str | None = None
    touches_edges: list[str] = Field(default_factory=list)
    occluded: bool | None = None
    notes: str = ""
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class AttentionRegion(StableModel):
    label: str = ""
    description: str = ""
    region: str = ""
    importance: str | None = None
    reason: str = ""
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class Subject(StableModel):
    label: str = ""
    description: str = ""
    prominence: str | None = None
    spatial: SpatialExtent = Field(default_factory=SpatialExtent)
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class Scene(StableModel):
    environment: str = ""
    location_type: str | None = None
    time_of_day: str | None = None
    weather: str | None = None
    mood: str | None = None


class Style(StableModel):
    medium: str = ""
    visual_style: str = ""
    color_palette: list[str] = Field(default_factory=list)
    lighting: str | None = None


class Composition(StableModel):
    layout: str = ""
    camera_angle: str | None = None
    depth: str | None = None
    focal_points: list[str] = Field(default_factory=list)
    notable_features: list[str] = Field(default_factory=list)
    foreground: list[str] = Field(default_factory=list)
    midground: list[str] = Field(default_factory=list)
    background: list[str] = Field(default_factory=list)
    negative_space: str = ""
    visual_balance: str = ""
    edge_content: list[str] = Field(default_factory=list)
    attention_regions: list[AttentionRegion] = Field(default_factory=list)


class VisualQuality(StableModel):
    overall: str = ""
    sharpness: str | None = None
    exposure: str | None = None
    noise: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class TextItem(StableModel):
    content: str = ""
    location: str | None = None
    spatial: SpatialExtent = Field(default_factory=SpatialExtent)
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class TextRegion(StableModel):
    label: str = ""
    box_normalized: NormalizedBox | None = None
    location: str = ""
    readability: str = ""
    preserve_for_reframe: bool = False


class TextAnalysis(StableModel):
    has_visible_text: bool = False
    items: list[TextItem] = Field(default_factory=list)
    text_regions: list[TextRegion] = Field(default_factory=list)
    notes: str = ""


class Person(StableModel):
    label: str = "person"
    description: str = ""
    count: int | None = None
    apparent_activity: str | None = None
    visible_attributes: list[str] = Field(default_factory=list)
    spatial: SpatialExtent = Field(default_factory=SpatialExtent)
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class ObjectItem(StableModel):
    label: str = ""
    description: str = ""
    location: str | None = None
    spatial: SpatialExtent = Field(default_factory=SpatialExtent)
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class DynamicPotential(StableModel):
    level: str = ""
    cues: list[str] = Field(default_factory=list)
    natural_motion_elements: list[str] = Field(default_factory=list)
    camera_motion_affordances: list[str] = Field(default_factory=list)
    motion_risks: list[str] = Field(default_factory=list)
    notes: str = ""


class RiskItem(StableModel):
    type: str = ""
    description: str = ""
    severity: str = "low"
    confidence: float | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float | None:
        return _confidence(value)


class Confidence(StableModel):
    overall: float = 0.0
    notes: str = ""

    @field_validator("overall", mode="before")
    @classmethod
    def clamp_overall(cls, value: Any) -> float:
        if value is None:
            return 0.0
        return _confidence(value) or 0.0


class ImageAnalysis(StableModel):
    schema_version: str = SCHEMA_VERSION
    image_metadata: ImageMetadata = Field(default_factory=ImageMetadata)
    summary: str = ""
    detailed_description: str = ""
    subjects: list[Subject] = Field(default_factory=list)
    scene: Scene = Field(default_factory=Scene)
    style: Style = Field(default_factory=Style)
    composition: Composition = Field(default_factory=Composition)
    visual_quality: VisualQuality = Field(default_factory=VisualQuality)
    text: TextAnalysis = Field(default_factory=TextAnalysis)
    people: list[Person] = Field(default_factory=list)
    objects: list[ObjectItem] = Field(default_factory=list)
    spatial_map: SpatialMap = Field(default_factory=SpatialMap)
    dynamic_potential: DynamicPotential = Field(default_factory=DynamicPotential)
    reframe_constraints: ReframeConstraints = Field(default_factory=ReframeConstraints)
    content_complexity: ContentComplexity = Field(default_factory=ContentComplexity)
    framing_risks: list[RiskItem] = Field(default_factory=list)
    generation_risks: list[RiskItem] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    uncertainties: list[str] = Field(default_factory=list)
    raw_model_output: str | None = None
    validation_warnings: list[ValidationWarning] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def default_schema_version(cls, value: Any) -> str:
        return value or SCHEMA_VERSION
