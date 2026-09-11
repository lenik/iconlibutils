# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib make — derive local size/format variants from existing icons."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ..autoindex import normalize_size
from .project import (
    ProjectContext,
    find_local_files,
    icon_stem,
    replace_size_format_dirs,
)


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser(
        "make",
        help=_("create local size/format variants of existing icons"),
    )
    sp.add_argument(
        "-s",
        "--size",
        dest="sizes",
        action="append",
        default=[],
        metavar="SIZE",
        help=_("add an output size (repeatable; e.g. 64 or 64x64)"),
    )
    sp.add_argument(
        "-F",
        "--format",
        dest="formats",
        action="append",
        default=[],
        metavar="FMT",
        help=_("add an output format (repeatable; e.g. png, webp)"),
    )
    sp.add_argument(
        "names",
        nargs="+",
        metavar="NAME",
        help=_("local icon name(s) to expand"),
    )
    sp.set_defaults(_run=run)


def _prefer_source(paths: list[Path]) -> Path:
    rank = {".svg": 0, ".png": 1, ".webp": 2, ".jpg": 3, ".jpeg": 3}
    return sorted(paths, key=lambda p: (rank.get(p.suffix.lower(), 9), str(p)))[0]


def _parse_wh(size: str | None) -> tuple[int, int] | None:
    if not size:
        return None
    norm = normalize_size(size)
    w_s, _, h_s = norm.partition("x")
    return int(w_s), int(h_s)


def _rasterize(src: Path, dest: Path, wh: tuple[int, int] | None, fmt: str) -> None:
    """Write *dest* in *fmt*, optionally sized to *wh*."""
    from PIL import Image

    fmt = fmt.lower().lstrip(".")
    if fmt == "jpeg":
        fmt = "jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() == ".svg" and fmt == "svg":
        if wh is not None:
            raise ValueError("cannot apply -s/--size to SVG output")
        if dest.resolve() != src.resolve():
            shutil.copy2(src, dest)
        return

    # Load source pixels.
    if src.suffix.lower() == ".svg":
        size = wh or (256, 256)
        from ..svgconv import svg_to_pil

        img = svg_to_pil(
            src, width=size[0], height=size[1], background_color="rgba(0,0,0,0)"
        )
    else:
        img = Image.open(src).convert("RGBA")
        if wh is not None:
            img = img.resize(wh, Image.Resampling.LANCZOS)

    if fmt == "png":
        img.save(dest, format="PNG")
    elif fmt == "webp":
        img.save(dest, format="WEBP")
    elif fmt in ("jpg", "jpeg"):
        rgb = Image.new("RGB", img.size, (255, 255, 255))
        rgb.paste(img, mask=img.split()[3])
        rgb.save(dest, format="JPEG", quality=90)
    else:
        raise ValueError(f"unsupported output format {fmt!r}")


def run(args: argparse.Namespace) -> int:
    sizes = list(args.sizes or [])
    formats = [f.lower().lstrip(".") for f in (args.formats or [])]
    formats = [("jpg" if f == "jpeg" else f) for f in formats]

    if not sizes and not formats:
        print(
            "iconlib: make requires at least one -s/--size or -F/--format",
            file=sys.stderr,
        )
        return 1

    ctx = ProjectContext(args)
    try:
        root = ctx.require_local_root()
    except FileNotFoundError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    # Cartesian product; missing axis means "keep source's own".
    size_opts: list[str | None] = sizes if sizes else [None]
    format_opts: list[str | None] = formats if formats else [None]

    made = 0
    errors = 0
    for raw in args.names:
        name = icon_stem(raw)
        paths = find_local_files(root, name)
        if not paths:
            print(f"iconlib: {name}: not found under {root}", file=sys.stderr)
            errors += 1
            continue
        src = _prefer_source(paths)
        src_rel = src.relative_to(root)
        src_fmt = src.suffix.lstrip(".").lower()
        if src_fmt == "jpeg":
            src_fmt = "jpg"

        for size in size_opts:
            for fmt in format_opts:
                out_fmt = fmt or src_fmt
                try:
                    rel = replace_size_format_dirs(src_rel, size=size, fmt=out_fmt)
                    dest = root / rel
                    if dest.resolve() == src.resolve():
                        continue
                    _rasterize(src, dest, _parse_wh(size), out_fmt)
                except (ValueError, RuntimeError, OSError) as e:
                    print(f"iconlib: {name}: {e}", file=sys.stderr)
                    errors += 1
                    continue
                made += 1
                if ctx.verbose > 0:
                    print(f"iconlib: make {src} -> {dest}", file=sys.stderr)

    if made == 0:
        return 1
    if ctx.verbose >= 0:
        print(_("Made {n} local variant file(s)").format(n=made))
    return 1 if errors else 0
