# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""SVG → raster helpers (cairosvg)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def svg_to_png_bytes(
    path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    background_color: str | None = None,
) -> bytes:
    """Rasterize an SVG with cairosvg; return PNG bytes."""
    try:
        import cairosvg
    except ImportError as e:
        raise RuntimeError(
            "cairosvg is required for SVG conversion; install python3-cairosvg"
        ) from e

    kwargs: dict = {"url": path.resolve().as_uri()}
    if width is not None:
        kwargs["output_width"] = width
    if height is not None:
        kwargs["output_height"] = height
    if background_color is not None:
        kwargs["background_color"] = background_color
    try:
        data = cairosvg.svg2png(**kwargs)
    except Exception as e:
        raise RuntimeError(f"SVG rasterize failed for {path}: {e}") from e
    if not data:
        raise RuntimeError(f"SVG rasterize produced no data for {path}")
    return data


def svg_to_pil(
    path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    background_color: str | None = None,
):
    """Rasterize SVG and return a PIL RGBA image."""
    from PIL import Image

    png = svg_to_png_bytes(
        path, width=width, height=height, background_color=background_color
    )
    return Image.open(BytesIO(png)).convert("RGBA")
