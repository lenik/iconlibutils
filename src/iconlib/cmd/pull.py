# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib pull — copy matching icons into the project."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ..autoindex import IconAsset, filter_assets, parse_size_args
from .context import Context

SCHEMA_ALIASES = {
    "o": "orig",
    "orig": "orig",
    "l": "lib",
    "lib": "lib",
    "f": "fmt",
    "fmt": "fmt",
    "n": "name",
    "name": "name",
    "s": "size",
    "size": "size",
    "v": "variant",
    "variant": "variant",
    "m": "stem",
    "stem": "stem",
    "e": "extension",
    "extension": "extension",
}


def parse_schema(schema: str) -> list[str]:
    if not schema or not schema.strip():
        raise ValueError("empty schema")
    tokens: list[str] = []
    for part in schema.split("/"):
        part = part.strip()
        if not part:
            continue
        key = SCHEMA_ALIASES.get(part)
        if key is None:
            raise ValueError(f"unknown schema token {part!r}")
        tokens.append(key)
    if not tokens:
        raise ValueError("empty schema")
    return tokens


def map_dirname(library: str, maps: dict[str, str] | None) -> str:
    if maps and library in maps:
        return maps[library]
    return library


def size_segment(
    asset: IconAsset,
    size_aliases: dict[str, str] | None,
) -> str:
    """Directory segment for schema ``s`` (alias name, size token, or ``none``)."""
    if not asset.size:
        return "none"
    if size_aliases:
        for alias, target in size_aliases.items():
            if asset.size == target:
                return alias
    return asset.size


def variant_segment(asset: IconAsset) -> str:
    return asset.variant or "none"


def expand_dest(
    asset: IconAsset,
    schema: str,
    *,
    maps: dict[str, str] | None = None,
    size_aliases: dict[str, str] | None = None,
) -> Path:
    tokens = parse_schema(schema)
    parts: list[str] = []
    for tok in tokens:
        if tok == "orig":
            parts.extend(Path(asset.orig).parts)
        elif tok == "lib":
            parts.append(map_dirname(asset.library, maps))
        elif tok == "fmt":
            parts.append(asset.format)
        elif tok == "name":
            parts.append(f"{asset.name}.{asset.format}")
        elif tok == "size":
            parts.append(size_segment(asset, size_aliases))
        elif tok == "variant":
            parts.append(variant_segment(asset))
        elif tok == "stem":
            parts.append(asset.name)
        elif tok == "extension":
            parts.append(asset.format)
        else:
            raise ValueError(f"internal schema token {tok!r}")
    return Path(*parts)


def register(sub: argparse._SubParsersAction) -> None:
    pp = sub.add_parser("pull", help=_("retrieve icons to the project"))
    pp.add_argument(
        "-F",
        "--format",
        dest="formats",
        action="append",
        default=[],
        metavar="FORMAT",
        help=_("add a format (repeatable); default all"),
    )
    pp.add_argument(
        "-S",
        "--size",
        dest="sizes",
        action="append",
        default=[],
        metavar="SIZE",
        help=_("add an image size or alias=size (repeatable)"),
    )
    pp.add_argument("pattern", nargs="?", default="")
    pp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = Context(args)
    formats = {f.lower().lstrip(".") for f in (ctx.args.formats or [])} or None
    if formats:
        formats = {("jpg" if f == "jpeg" else f) for f in formats}
    size_wanted, size_aliases = parse_size_args(ctx.args.sizes or [])
    sizes = size_wanted or None

    groups = ctx.matched_groups(ctx.args.pattern)
    if not groups:
        print("iconlib: no icons matched", file=sys.stderr)
        return 1

    dest_root = ctx.project_dir / ctx.local_dir
    copied = 0
    for g in groups:
        if formats or sizes:
            assets = filter_assets(g.assets, formats, sizes)
        else:
            assets = list(g.assets)
        if not assets:
            continue

        seen: set[tuple] = set()
        for a in sorted(
            assets, key=lambda x: (x.library, x.format, x.size or "", x.orig)
        ):
            key = (a.library, a.format, a.size, a.variant, a.name)
            if key in seen:
                continue
            seen.add(key)
            rel = expand_dest(
                a, ctx.schema, maps=ctx.maps, size_aliases=size_aliases or None
            )
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.path, dest)
            copied += 1
            if ctx.verbose > 0:
                print(f"iconlib: {a.path} -> {dest}", file=sys.stderr)

    if copied == 0:
        print("iconlib: no assets copied", file=sys.stderr)
        return 1
    if ctx.verbose >= 0:
        print(_("Copied {n} file(s) into {dir}").format(n=copied, dir=dest_root))
    return 0
