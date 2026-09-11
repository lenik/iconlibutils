#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Auto-index icon libraries by walking image trees."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from paths import Library

IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "Fonts",
    "fonts",
    "packages",
    "tools",
    "scripts",
    ".github",
    ".vscode",
    ".changeset",
    "__pycache__",
}

VARIANT_NAMES = frozenset(
    {
        "outline",
        "filled",
        "solid",
        "regular",
        "bold",
        "light",
        "thin",
        "duotone",
        "micro",
        "mini",
        "normal",
        "flat",
        "line",
        "gradient",
        "neon",
        "pop",
        "remix",
        "duo",
        "color",
        "black",
        "colors",
    }
)

FORMAT_DIR_NAMES = frozenset({"svg", "png", "jpg", "jpeg", "webp", "SVGs", "PNGs"})

SIZE_RE = re.compile(r"^(\d+)x(\d+)$", re.I)
BARE_SIZE_RE = re.compile(r"^(\d+)$")

# Prefer svg, then common outline-ish variants.
FORMAT_RANK = {"svg": 0, "png": 1, "jpg": 2, "jpeg": 2, "webp": 3}
VARIANT_RANK = {
    "outline": 0,
    "regular": 1,
    "normal": 2,
    "line": 3,
    "mini": 4,
    "micro": 5,
    "solid": 10,
    "filled": 11,
    "bold": 12,
    "fill": 13,
}


@dataclass(frozen=True)
class IconAsset:
    library: str
    name: str
    orig: str
    path: Path
    format: str
    size: str | None = None
    variant: str | None = None


@dataclass
class IconGroup:
    name: str
    assets: list[IconAsset] = field(default_factory=list)

    def formats(self) -> list[str]:
        return sorted({a.format for a in self.assets})

    def sizes(self) -> list[str]:
        return sorted({a.size for a in self.assets if a.size})


def normalize_format(ext: str) -> str:
    e = ext.lower().lstrip(".")
    if e == "jpeg":
        return "jpg"
    return e


def _size_token(part: str) -> str | None:
    m = SIZE_RE.match(part)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    return None


def parse_rel_path(rel: Path) -> tuple[str, str | None, str | None, str]:
    """
    Return (name, size, variant, format) from a path relative to library root.
    """
    parts = list(rel.parts)
    stem = rel.stem
    fmt = normalize_format(rel.suffix)

    size: str | None = None
    variant: str | None = None
    parent_parts = parts[:-1]

    for i, part in enumerate(parent_parts):
        st = _size_token(part)
        if st:
            size = st
            continue
        low = part.lower()
        if low in VARIANT_NAMES or part in VARIANT_NAMES:
            variant = low
            continue
        # bare numeric size when previous/next looks like format/variant (heroicons png/16/..)
        if BARE_SIZE_RE.match(part):
            prev = parent_parts[i - 1].lower() if i > 0 else ""
            nxt = parent_parts[i + 1].lower() if i + 1 < len(parent_parts) else ""
            if (
                prev in FORMAT_DIR_NAMES
                or prev in {v.lower() for v in VARIANT_NAMES}
                or nxt in VARIANT_NAMES
                or prev in {"png", "jpg", "svg", "webp"}
            ):
                n = int(part)
                size = f"{n}x{n}"

    # Strip trailing -<variant> from stem when variant is in path (Phosphor).
    name = stem
    if variant:
        suffix = f"-{variant}"
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
        # also handle -fill vs filled mismatch for phosphor fill
        if variant in ("filled", "fill") and name.lower().endswith("-fill"):
            name = name[:-5]

    return name, size, variant, fmt


def iter_assets(lib: Library) -> list[IconAsset]:
    root = lib.path
    if not root.is_dir():
        return []

    assets: list[IconAsset] = []
    for dirpath, dirnames, filenames in os_walk_skip(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in IMAGE_EXTS:
                continue
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue
            name, size, variant, fmt = parse_rel_path(rel)
            assets.append(
                IconAsset(
                    library=lib.name,
                    name=name,
                    orig=rel.as_posix(),
                    path=p,
                    format=fmt,
                    size=size,
                    variant=variant,
                )
            )
    return assets


def os_walk_skip(root: Path):
    import os

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        yield dirpath, dirnames, filenames


def index_libraries(libs: list[Library]) -> dict[str, IconGroup]:
    groups: dict[str, IconGroup] = {}
    for lib in libs:
        for asset in iter_assets(lib):
            g = groups.get(asset.name)
            if g is None:
                g = IconGroup(name=asset.name)
                groups[asset.name] = g
            g.assets.append(asset)
    return groups


def compile_pattern(pattern: str | None):
    """Return a predicate name -> bool."""
    if pattern is None or pattern == "":
        return lambda _name: True
    if pattern.startswith("/"):
        rx = re.compile(pattern[1:])
        return lambda name: rx.search(name) is not None
    if any(c in pattern for c in "*?["):
        return lambda name: fnmatch.fnmatch(name, pattern)
    return lambda name: name == pattern


def filter_groups(
    groups: dict[str, IconGroup],
    pattern: str | None = None,
    libraries: set[str] | None = None,
) -> list[IconGroup]:
    pred = compile_pattern(pattern)
    out: list[IconGroup] = []
    for name in sorted(groups):
        if not pred(name):
            continue
        g = groups[name]
        if libraries is not None:
            assets = [a for a in g.assets if a.library in libraries]
            if not assets:
                continue
            g = IconGroup(name=name, assets=assets)
        out.append(g)
    return out


def search_groups(
    groups: dict[str, IconGroup],
    pattern: str | None = None,
    libraries: set[str] | None = None,
) -> list[tuple[float, IconGroup]]:
    """
    Return (score, group) pairs sorted by score descending, then name.

    Plain English queries use inflection + WordNet expansion. Glob, regex,
    and empty patterns keep boolean matching (score 1.0 for hits, 0 for all).
    """
    from semantic import (
        SCORE_THRESHOLD,
        expand_query_terms,
        is_plain_query,
        score_icon_name,
    )

    def narrow(g: IconGroup) -> IconGroup | None:
        if libraries is None:
            return g
        assets = [a for a in g.assets if a.library in libraries]
        if not assets:
            return None
        return IconGroup(name=g.name, assets=assets)

    if not is_plain_query(pattern):
        hits = filter_groups(groups, pattern, libraries)
        # empty pattern → score 0; glob/regex hits → 1
        base = 0.0 if not pattern else 1.0
        return [(base, g) for g in hits]

    assert pattern is not None
    query_terms = expand_query_terms(pattern)
    scored: list[tuple[float, IconGroup]] = []
    for name, g in groups.items():
        ng = narrow(g)
        if ng is None:
            continue
        score = score_icon_name(name, pattern, query_terms)
        if score >= SCORE_THRESHOLD:
            scored.append((score, ng))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return scored


def asset_rank(a: IconAsset) -> tuple:
    return (
        FORMAT_RANK.get(a.format, 99),
        VARIANT_RANK.get(a.variant or "", 50),
        a.size or "",
        a.orig,
    )


def prefer_asset(
    assets: list[IconAsset],
    formats: set[str] | None = None,
    sizes: set[str] | None = None,
) -> IconAsset | None:
    cand = assets
    if formats:
        cand = [a for a in cand if a.format in formats]
    if sizes:
        cand = [a for a in cand if a.size and normalize_size(a.size) in sizes]
    if not cand:
        return None
    return sorted(cand, key=asset_rank)[0]


def normalize_size(token: str) -> str:
    """Normalize size token to WxH form when possible."""
    token = token.strip()
    m = SIZE_RE.match(token)
    if m:
        return f"{int(m.group(1))}x{int(m.group(2))}"
    if BARE_SIZE_RE.match(token):
        n = int(token)
        return f"{n}x{n}"
    return token


def parse_size_args(raw_sizes: list[str]) -> tuple[set[str], dict[str, str]]:
    """
    Parse -S values.

    Returns (normalized size set for matching, alias_name -> normalized size).
    Alias forms: medium=32x32 or medium=32.
    Bare forms: 16, 16x16.
    """
    wanted: set[str] = set()
    aliases: dict[str, str] = {}
    for raw in raw_sizes:
        if "=" in raw:
            alias, val = raw.split("=", 1)
            norm = normalize_size(val)
            aliases[alias] = norm
            wanted.add(norm)
        else:
            wanted.add(normalize_size(raw))
    return wanted, aliases


def filter_assets(
    assets: list[IconAsset],
    formats: set[str] | None = None,
    sizes: set[str] | None = None,
) -> list[IconAsset]:
    out = assets
    if formats:
        out = [a for a in out if a.format in formats]
    if sizes:
        out = [a for a in out if a.size and normalize_size(a.size) in sizes]
    return out
