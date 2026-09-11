#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Load and resolve icon library path registries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Library:
    type: str
    name: str
    path: Path


DEFAULT_PATH_FILES = (
    Path("/etc/iconlibutils/path"),
    Path.home() / ".config" / "iconlibutils" / "path",
)


def parse_path_file(path: Path) -> list[Library]:
    if not path.is_file():
        return []
    libs: list[Library] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"{path}:{lineno}: expected TYPE NAME PATH")
        typ, name, *rest = parts
        lib_path = Path(" ".join(rest)).expanduser()
        libs.append(Library(type=typ, name=name, path=lib_path))
    return libs


def load_libraries(
    path_files: list[Path] | None = None,
    extra: list[Library] | None = None,
) -> dict[str, Library]:
    """Load registries; later files override earlier ones by name."""
    files = list(path_files) if path_files is not None else list(DEFAULT_PATH_FILES)
    by_name: dict[str, Library] = {}
    for pf in files:
        for lib in parse_path_file(pf):
            by_name[lib.name] = lib
    if extra:
        for lib in extra:
            by_name[lib.name] = lib
    return by_name


def resolve_library_names(
    registry: dict[str, Library],
    specs: list[str] | None,
) -> list[Library]:
    """
    Resolve library selectors.

    If specs is None or empty, return all registered libraries (sorted by name).
    Each spec must uniquely prefix-match a registered name, or equal a name.
    """
    if not specs:
        return [registry[k] for k in sorted(registry)]

    resolved: list[Library] = []
    seen: set[str] = set()
    for spec in specs:
        matches = [n for n in registry if n == spec or n.startswith(spec)]
        if not matches:
            raise KeyError(f"no library matching {spec!r}")
        # Prefer exact match when present.
        if spec in registry:
            name = spec
        elif len(matches) == 1:
            name = matches[0]
        else:
            # unambiguous prefix: only one match that starts with spec
            # if multiple, error
            raise KeyError(
                f"ambiguous library {spec!r}: matches {', '.join(sorted(matches))}"
            )
        if name not in seen:
            seen.add(name)
            resolved.append(registry[name])
    return resolved


def env_path_files() -> list[Path]:
    """Allow tests to override path file list via ICONLIBUTILS_PATH_FILES (os.pathsep)."""
    raw = os.environ.get("ICONLIBUTILS_PATH_FILES")
    if not raw:
        return list(DEFAULT_PATH_FILES)
    return [Path(p) for p in raw.split(os.pathsep) if p]
