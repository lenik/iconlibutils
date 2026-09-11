#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Expand pull destination paths from schema tokens."""

from __future__ import annotations

from pathlib import Path

from autoindex import IconAsset

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
    """
    Directory segment for schema `s`.

    Prefer alias name when this asset's size matches an alias target;
    else use the asset size token; else `none`.
    """
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
