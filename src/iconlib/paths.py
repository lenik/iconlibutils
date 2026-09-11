# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Discover icon libraries via pkgdatadir library metadata.

Primary discovery (drop-in files)::

    <pkgdatadir>/library/<name>

Each file is key=value metadata. Packaged sources ship as
``library.iconlib`` and meson renames on install to ``<name>``.

Optional legacy path registries (``TYPE NAME PATH``) remain supported.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .site import default_icon_datadir, get_pkgdatadir


@dataclass(frozen=True)
class Library:
    type: str
    name: str
    path: Path
    title: str = ""
    license: str = ""
    homepage: str = ""
    description: str = ""
    meta_path: Path | None = field(default=None, compare=False)


DEFAULT_PATH_FILES = (
    Path("/etc/iconlibutils/path"),
    Path.home() / ".config" / "iconlibutils" / "path",
)

# Skip obvious non-metadata files in the library drop-in dir.
_SKIP_SUFFIXES = {".md", ".txt", ".html", ".css", ".js", ".json", ".png", ".svg"}


def default_library_dirs() -> tuple[Path, ...]:
    return (
        get_pkgdatadir() / "library",
        Path.home() / ".config" / "iconlibutils" / "library",
    )


def parse_library_conf(path: Path) -> dict[str, str]:
    """Parse key=value library metadata (comments and blank lines allowed)."""
    data: dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{lineno}: expected key=value")
        key, _, val = line.partition("=")
        data[key.strip().lower()] = val.strip()
    return data


def library_from_data(
    data: dict[str, str],
    *,
    default_name: str,
    meta_path: Path | None = None,
) -> Library:
    name = data.get("name") or default_name
    lib_path = data.get("path") or data.get("datadir")
    if not lib_path:
        lib_path = str(default_icon_datadir(name))
    typ = data.get("type") or "auto"
    return Library(
        type=typ,
        name=name,
        path=Path(lib_path).expanduser(),
        title=data.get("title") or name,
        license=data.get("license") or "",
        homepage=data.get("homepage") or "",
        description=data.get("description") or "",
        meta_path=meta_path,
    )


def library_from_meta_file(meta_file: Path) -> Library | None:
    """Load one library from a drop-in file ``.../library/<name>``."""
    if not meta_file.is_file():
        return None
    if meta_file.name.startswith("."):
        return None
    if meta_file.suffix.lower() in _SKIP_SUFFIXES:
        return None
    try:
        data = parse_library_conf(meta_file)
    except ValueError:
        return None
    # Require at least one known key so random files are ignored.
    if not any(k in data for k in ("name", "path", "type", "package", "title")):
        return None
    default_name = meta_file.stem if meta_file.suffix else meta_file.name
    return library_from_data(data, default_name=default_name, meta_path=meta_file)


def scan_library_dir(root: Path) -> list[Library]:
    if not root.is_dir():
        return []
    libs: list[Library] = []
    for child in sorted(root.iterdir()):
        if child.name.startswith("."):
            continue
        if not child.is_file():
            continue
        lib = library_from_meta_file(child)
        if lib is not None:
            libs.append(lib)
    return libs


def parse_path_file(path: Path) -> list[Library]:
    """Legacy ``TYPE NAME PATH`` registry file."""
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


def env_library_dirs() -> list[Path]:
    raw = os.environ.get("ICONLIBUTILS_LIBRARY_DIRS")
    if raw:
        return [Path(p) for p in raw.split(os.pathsep) if p]
    return list(default_library_dirs())


def env_path_files() -> list[Path]:
    raw = os.environ.get("ICONLIBUTILS_PATH_FILES")
    if raw == "":
        return []
    if raw:
        return [Path(p) for p in raw.split(os.pathsep) if p]
    return list(DEFAULT_PATH_FILES)


def load_libraries(
    library_dirs: list[Path] | None = None,
    path_files: list[Path] | None = None,
    extra: list[Library] | None = None,
) -> dict[str, Library]:
    """Discover libraries; later sources override earlier ones by name.

    Order:
      1. system/user ``library/<name>`` drop-in files
      2. optional legacy path files
      3. ``extra``
    """
    dirs = list(library_dirs) if library_dirs is not None else env_library_dirs()
    files = list(path_files) if path_files is not None else env_path_files()

    by_name: dict[str, Library] = {}
    for d in dirs:
        for lib in scan_library_dir(d):
            by_name[lib.name] = lib
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
    if not specs:
        return [registry[k] for k in sorted(registry)]

    resolved: list[Library] = []
    seen: set[str] = set()
    for spec in specs:
        matches = [n for n in registry if n == spec or n.startswith(spec)]
        if not matches:
            raise KeyError(f"no library matching {spec!r}")
        if spec in registry:
            name = spec
        elif len(matches) == 1:
            name = matches[0]
        else:
            raise KeyError(
                f"ambiguous library {spec!r}: matches {', '.join(sorted(matches))}"
            )
        if name not in seen:
            seen.add(name)
            resolved.append(registry[name])
    return resolved
