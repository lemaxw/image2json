#!/usr/bin/env python3
"""Benchmark script for testing different Ollama configurations."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from image2json.analyzer import ImageAnalyzer
from image2json.config import AnalysisConfig


def benchmark_config(
    image_path: Path,
    model: str,
    max_image_side: int,
    temperature: float,
    timeout: float = 600.0,
) -> dict[str, Any]:
    """Run a single benchmark with given configuration."""
    config = AnalysisConfig(
        model=model,
        max_image_side=max_image_side,
        temperature=temperature,
        timeout=timeout,
    )
    analyzer = ImageAnalyzer(config)
    
    start_time = time.time()
    result = analyzer.analyze_path(image_path)
    elapsed = time.time() - start_time
    
    return {
        "model": model,
        "max_image_side": max_image_side,
        "temperature": temperature,
        "elapsed_seconds": round(elapsed, 2),
        "schema_version": result.schema_version,
        "subjects_count": len(result.subjects),
        "objects_count": len(result.objects),
        "people_count": len(result.people),
        "has_text": result.text.has_visible_text,
        "confidence": result.confidence.overall,
    }


def main() -> None:
    """Run benchmarks with different configurations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Ollama configurations")
    parser.add_argument("image_path", type=Path, help="Path to test image")
    parser.add_argument("--models", nargs="+", default=["qwen3-vl:8b"], help="Models to test")
    parser.add_argument("--max-image-sides", nargs="+", type=int, default=[1024, 800], help="Max image sides to test")
    parser.add_argument("--temperatures", nargs="+", type=float, default=[0.0], help="Temperatures to test")
    parser.add_argument("--timeout", type=float, default=600.0, help="Timeout per request")
    parser.add_argument("--output", type=Path, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    if not args.image_path.exists():
        raise FileNotFoundError(f"Image not found: {args.image_path}")
    
    results = []
    
    for model in args.models:
        for max_side in args.max_image_sides:
            for temp in args.temperatures:
                print(f"Testing: model={model}, max_image_side={max_side}, temperature={temp}")
                try:
                    result = benchmark_config(
                        args.image_path,
                        model=model,
                        max_image_side=max_side,
                        temperature=temp,
                        timeout=args.timeout,
                    )
                    results.append(result)
                    print(f"  ✓ {result['elapsed_seconds']}s, confidence={result['confidence']}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    results.append({
                        "model": model,
                        "max_image_side": max_side,
                        "temperature": temp,
                        "error": str(e),
                    })
    
    output = {
        "image_path": str(args.image_path),
        "results": results,
    }
    
    if args.output:
        args.output.write_text(json.dumps(output, indent=2) + "\n")
        print(f"\nResults saved to {args.output}")
    else:
        print("\n" + json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
