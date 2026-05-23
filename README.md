# image2json

`image2json` is a generic local image-to-JSON vision analysis tool. It accepts one image and returns a stable, general-purpose structured JSON description of the visual content.

The default backend is local Ollama using `qwen3-vl:8b` at `http://localhost:11434`. The initial implementation contains no external APIs, cloud services, telemetry, crop selection, video planning, social-media formatting, render backend logic, or downstream app adapters.

Downstream projects should convert this generic JSON into their own project-specific schemas.

## Setup

Using `uv`:

```bash
uv sync
ollama pull qwen3-vl:8b
```

Fallback with a project-local virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ollama pull qwen3-vl:8b
```

Do not install dependencies globally.

## Ollama Performance Optimization

For better performance, especially on RTX 3090 or similar GPUs:

**Environment variables** (set before starting Ollama):
```bash
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_OVERHEAD=0
export OLLAMA_LOAD_TIMEOUT=300
export OLLAMA_KEEP_ALIVE=30m
```

**Alternative models**:
- `llava` (7B) - Faster, good vision capabilities
- `qwen3-vl:8b` - Default model, more detailed but slower

**Image size**: Reduce `--max-image-side` from 1600 to 1024 or 800 for faster processing. Vision models work well with smaller images.

**Temperature**: Use `--temperature 0.0` for more deterministic (faster) output.

**Benchmark**: Test different configurations:
```bash
uv run python -m image2json.benchmark examples/sample.jpg --models qwen3-vl:8b llava --max-image-sides 1024 800 --output results.json
```

## CLI Usage

Analyze one local image:

```bash
uv run image2json analyze examples/sample.jpg
uv run image2json analyze examples/sample.jpg --output analysis.json --pretty
python -m image2json analyze examples/sample.jpg
```

Useful options:

```bash
uv run image2json analyze IMAGE_PATH \
  --model qwen3-vl:8b \
  --ollama-url http://localhost:11434 \
  --prompt-file prompts/vision_analysis.md \
  --output analysis.json \
  --pretty \
  --include-raw \
  --timeout 300 \
  --max-image-side 1600
```

**Short vs Full Analysis**:

By default, the tool uses a short prompt that asks the model for only `schema_version`,
`summary`, and `detailed_description` for faster analysis. The returned JSON still follows
the stable output schema, with omitted analysis fields filled by defaults. Use `--full`
for the complete detailed analysis:

```bash
# Short version (default, faster)
uv run image2json analyze IMAGE_PATH

# Full version (slower, comprehensive)
uv run image2json analyze IMAGE_PATH --full
```

Use `--no-raw` to omit raw model output from the returned JSON.

If you receive an empty analysis with `json_extraction_failed`, first verify the model can see the image directly:

```bash
ollama run qwen3-vl:8b /absolute/path/to/image.jpg "describe this image"
```

The Python client uses Ollama's local `/api/chat` endpoint with an image message and structured JSON output.
Local vision analysis can be slow for large images or detailed schemas. If a request times out, retry with a larger timeout:

```bash
uv run image2json analyze examples/sample.jpg --timeout 600
```

By default, the image sent to Ollama is resized so its longest side is at most `1600` pixels. The returned `image_metadata` still describes the original source image. Use `--max-image-side 0` to send the original image bytes.

## FastAPI Usage

Start the API:

```bash
uv run uvicorn image2json.api:app --reload
```

Or, inside an activated local `.venv`:

```bash
uvicorn image2json.api:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze an uploaded image:

```bash
curl -X POST "http://127.0.0.1:8000/analyze/upload?include_raw=false" \
  -F "file=@examples/sample.jpg"
```

Analyze a local image path:

```bash
curl -X POST "http://127.0.0.1:8000/analyze/path" \
  -H "Content-Type: application/json" \
  -d '{"image_path":"examples/sample.jpg","include_raw":false}'
```

## Tests

Using `uv`:

```bash
uv run pytest
```

Or, inside an activated local `.venv`:

```bash
pytest
```

Unit tests mock model responses and do not require a running Ollama server.

## Schema

The response schema is defined in `src/image2json/models.py`. Preserve backward compatibility by adding optional fields instead of removing or renaming existing fields.

Top-level fields:

- `schema_version`
- `image_metadata`
- `summary`
- `detailed_description`
- `subjects`
- `scene`
- `style`
- `composition`
- `visual_quality`
- `text`
- `people`
- `objects`
- `spatial_map`
- `dynamic_potential`
- `reframe_constraints`
- `content_complexity`
- `framing_risks`
- `generation_risks`
- `confidence`
- `uncertainties`
- `raw_model_output`
- `validation_warnings`

Validation warnings are structured objects. Missing, null, malformed, or invalid fields are normalized where possible so the final response remains JSON serializable.
When the model provides `composition.focal_points` but leaves `subjects` or `composition.attention_regions` empty, the validator derives minimal entries from the model-provided composition evidence and records `derived_field` warnings.
The analyzer reads source image dimensions locally and fills `image_metadata` deterministically.
If the model guesses different dimensions, the validator overrides them and records `model_metadata_overridden`.

### Spatial Description

The schema includes descriptive spatial cues so downstream projects can make their own layout or crop decisions later. `image2json` does not choose crop anchors, crop boxes, aspect ratios, output formats, or video plans.

Useful spatial fields include:

- `image_metadata`: source `width`, `height`, factual `orientation`, and source `aspect_ratio`.
- `subjects[].spatial`, `objects[].spatial`, `people[].spatial`, and `text.items[].spatial`: approximate plain-language placement such as `center`, `top-left`, `foreground`, `background`, `large`, `near left edge`, or `partially occluded`.
- `spatial_map.primary_regions`: normalized approximate boxes, centers, importance, edge margin, and whether the region should generally be preserved by downstream consumers.
- `composition.foreground`, `composition.midground`, and `composition.background`: scene layers.
- `composition.negative_space`: areas with relatively little important content.
- `composition.edge_content`: important visible content close to image edges.
- `composition.attention_regions`: visually important regions a downstream system may want to preserve, expressed as descriptive evidence only.
- `framing_risks`: edge contact, truncation, occlusion, or ambiguous boundaries that may matter to downstream consumers.
- `text.text_regions`: approximate text areas to preserve even when OCR content is partial or unreadable.
- `reframe_constraints`: generic preserve/avoid-cutting lists, whether the source composition is panoramic/wide, whether important content spans the full width, and vertical reframe risk.
- `content_complexity`: generic flags for dense detail, faces, hands, readable text, repeating patterns, and fine geometry.
- `dynamic_potential`: natural motion elements, camera motion affordances, and motion risks, expressed as general physical observations.

## Prompt

The main model instruction lives in `prompts/vision_analysis.md`. It asks the model to return one JSON object only and to avoid inventing invisible details.

## Example JSON Response

```json
{
  "schema_version": "1.0",
  "image_metadata": {
    "width": 1920,
    "height": 1080,
    "orientation": "landscape",
    "aspect_ratio": 1.7778
  },
  "summary": "A person standing near a table with several visible objects.",
  "detailed_description": "The image shows an indoor scene with a central human subject and objects arranged on a nearby surface.",
  "subjects": [
    {
      "label": "person",
      "description": "A visible person is the main subject.",
      "prominence": "primary",
      "spatial": {
        "region": "center",
        "x_position": "center",
        "y_position": "center",
        "distance_layer": "midground",
        "relative_size": "large",
        "touches_edges": [],
        "occluded": false,
        "notes": "The person is visually central and unobstructed.",
        "confidence": 0.82
      },
      "confidence": 0.82
    }
  ],
  "scene": {
    "environment": "indoor",
    "location_type": null,
    "time_of_day": null,
    "weather": null,
    "mood": "neutral"
  },
  "style": {
    "medium": "photograph",
    "visual_style": "natural",
    "color_palette": ["neutral", "dark", "light"],
    "lighting": "ambient"
  },
  "composition": {
    "layout": "central subject with surrounding objects",
    "camera_angle": "eye-level",
    "depth": "moderate",
    "focal_points": ["person", "table"],
    "notable_features": [],
    "foreground": ["near edge of table"],
    "midground": ["person", "main objects on table"],
    "background": ["indoor wall"],
    "negative_space": "upper background has relatively low visual detail",
    "visual_balance": "main subject centered with supporting objects lower in frame",
    "edge_content": [],
    "attention_regions": [
      {
        "label": "person and table",
        "description": "The primary subject and the nearby objects form the most important visible region.",
        "region": "center and lower-center",
        "importance": "primary",
        "reason": "Contains the main subject and contextual objects.",
        "confidence": 0.84
      }
    ]
  },
  "visual_quality": {
    "overall": "usable",
    "sharpness": "moderate",
    "exposure": "balanced",
    "noise": null,
    "artifacts": [],
    "confidence": 0.75
  },
  "text": {
    "has_visible_text": false,
    "items": [],
    "text_regions": [],
    "notes": ""
  },
  "people": [
      {
        "label": "person",
        "description": "One visible person.",
      "count": 1,
      "apparent_activity": null,
      "visible_attributes": [],
      "spatial": {
        "region": "center",
        "x_position": "center",
        "y_position": "center",
        "distance_layer": "midground",
        "relative_size": "large",
        "touches_edges": [],
        "occluded": false,
        "notes": "",
        "confidence": 0.8
      },
      "confidence": 0.8
    }
  ],
  "objects": [],
  "spatial_map": {
    "primary_regions": [
      {
        "label": "person and table",
        "box_normalized": {"x": 0.25, "y": 0.2, "w": 0.5, "h": 0.65},
        "center": {"x": 0.5, "y": 0.525},
        "importance": "primary",
        "edge_margin": "safe",
        "preserve_for_reframe": true
      }
    ],
    "important_regions_span": "moderate",
    "safe_reframe_difficulty": "medium"
  },
  "dynamic_potential": {
    "level": "low",
    "cues": ["depth layers"],
    "natural_motion_elements": ["depth layers"],
    "camera_motion_affordances": ["gentle push-in"],
    "motion_risks": ["face drift"],
    "notes": "No strong motion cues are visible."
  },
  "reframe_constraints": {
    "must_preserve": ["person", "table"],
    "avoid_cutting": [],
    "wide_composition": true,
    "full_width_important_content": false,
    "vertical_crop_risk": "medium",
    "reason": "The primary content is central, but the source frame is wide."
  },
  "content_complexity": {
    "level": "medium",
    "dense_details": false,
    "faces": true,
    "hands": false,
    "readable_text": false,
    "repeating_patterns": false,
    "fine_geometry": false
  },
  "framing_risks": [],
  "generation_risks": [],
  "confidence": {
    "overall": 0.78,
    "notes": "Some details are uncertain."
  },
  "uncertainties": [],
  "raw_model_output": null,
  "validation_warnings": []
}
```

## MemPalace Usage

At the start of work, use `/mempalace:help` or `mempalace instructions help` to view available memory commands. Later, use `/mempalace:mine` or `mempalace mine .` to store the project, and `/mempalace:search` or `mempalace search "image2json schema"` to retrieve decisions.
