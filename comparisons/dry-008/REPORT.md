# dry-008 image2json comparison

The legacy analysis was read from the latest successful `debug_*.json` in each
corresponding `dry-008` folder. New analyses were generated from the original source
images with the improved full-analysis prompt and compact inference schema.

| Folder | Legacy result | New result | Assessment |
|---|---|---|---|
| `0__MG_0006` | Correct temple description, but only one subject/region; no text, framing risks, or generation risks | Separates temple, rocky foreground, and sky; detects the photographer watermark; adds spatial regions, cloud motion, sound, framing, and architecture/detail risks | Better |
| `1_20260627_130019` | Both recorded attempts timed out without analysis | Complete valley, stream, flowering shrub, mist, foliage/water motion, rushing-water sound, reframe constraints, and generation risks | Better (replaces failure) |
| `2_DSC05444` | Correct mannequin row, but only one subject/region and no watermark or risk analysis | Separates mannequins, garments, lighting, and floor; detects watermark; records edge truncation, fabric/detail risks, and preservation regions | Better |
| `3_DSC04483` | Correct waterfront scene, but only one spatial region and no framing/generation risks or watermark | Preserves building/water/walkway/reflections separately; detects watermark; adds reflection motion, waterfront sound, framing, and reflection/detail risks | Better |
| `4_DSC08334` | Timed out without analysis | Complete skyline analysis including structural frame, trees, construction detail, watermark, spatial regions, city soundscape, and generation risks | Better (replaces failure) |
| `5_DSC00233` | Correct desert/road/camp description, but no text or framing/generation risks | Detects watermark, separates five preservation regions, follows the winding road for camera motion, and adds vehicle/terrain framing and generation risks | Better |
| `6_20250516_125456` | Correct street scene and a partial graffiti text region; grouped the two riders into one person record and omitted framing/generation risks | Retains the graffiti text region, separates both riders and the pedestrian, maps five preservation regions, and adds scooter/traffic sound, framing, face, foliage, and graffiti-detail risks | Better |

## Comparison criteria

- factual agreement with the source image
- main-subject and people coverage
- visible text and watermark handling
- useful normalized preservation regions
- natural and camera motion grounded in visible content
- plausible local sound without unsupported sources
- reframe constraints and edge risks
- image-to-video generation risks
- absence of empty OCR records, unsupported motion categories, and validation errors

All seven new files use the stable public `ImageAnalysis` schema and omit raw model
output. The original debug files and source images were not modified.
