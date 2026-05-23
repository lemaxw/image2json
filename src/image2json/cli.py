from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import typer

from image2json.analyzer import ImageAnalyzer
from image2json.config import (
    AnalysisConfig,
    DEFAULT_MAX_IMAGE_SIDE,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_SHORT_VERSION,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)
from image2json.json_utils import dump_analysis
from image2json.ollama_client import OllamaError

app = typer.Typer(help="Analyze local images into stable, general-purpose JSON.")


@app.callback()
def main() -> None:
    """Local image-to-JSON tools."""


@app.command()
def analyze(
    image_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True, help="Local image path.")],
    model: Annotated[str, typer.Option("--model", help="Local Ollama vision model.")] = DEFAULT_MODEL,
    ollama_url: Annotated[str, typer.Option("--ollama-url", help="Local Ollama base URL.")] = DEFAULT_OLLAMA_URL,
    prompt_file: Annotated[Path | None, typer.Option("--prompt-file", exists=True, dir_okay=False, readable=True)] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write JSON to a file.")] = None,
    pretty: Annotated[bool, typer.Option("--pretty/--compact", help="Pretty-print or compact JSON.")] = True,
    include_raw: Annotated[bool, typer.Option("--include-raw/--no-raw", help="Include raw model output.")] = True,
    timeout: Annotated[float, typer.Option("--timeout", help="Ollama request timeout in seconds.")] = DEFAULT_TIMEOUT_SECONDS,
    temperature: Annotated[float, typer.Option("--temperature", help="Sampling temperature (0.0 for deterministic).")] = DEFAULT_TEMPERATURE,
    max_image_side: Annotated[
        int,
        typer.Option(
            "--max-image-side",
            help="Resize the image sent to Ollama so its longest side is at most this many pixels. Use 0 to disable.",
        ),
    ] = DEFAULT_MAX_IMAGE_SIDE,
    short_version: Annotated[
        bool,
        typer.Option(
            "--short/--full",
            help="Output only summary and detailed_description (short) or full analysis (full).",
        ),
    ] = DEFAULT_SHORT_VERSION,
) -> None:
    config = AnalysisConfig(
        model=model,
        ollama_url=ollama_url,
        prompt_file=prompt_file,
        timeout=timeout,
        temperature=temperature,
        max_image_side=max_image_side,
        short_version=short_version,
    )
    try:
        analysis_result = ImageAnalyzer(config).analyze_path(image_path)
    except (FileNotFoundError, ValueError, OllamaError) as exc:
        raise click.ClickException(str(exc)) from exc
    rendered = dump_analysis(analysis_result, include_raw=include_raw, pretty=pretty)
    if output:
        output.write_text(rendered + "\n", encoding="utf-8")
    else:
        typer.echo(rendered)
