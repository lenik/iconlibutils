# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Project-local asset helpers (no library index required)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..autoindex import FORMAT_DIR_NAMES, IMAGE_EXTS, SIZE_RE, BARE_SIZE_RE, normalize_size
from ..rc import load_rc

_FORMAT_PARTS = {x.lower() for x in FORMAT_DIR_NAMES} | {
    "svg",
    "png",
    "jpg",
    "jpeg",
    "webp",
}


class ProjectContext:
    """Resolve project-dir / local-dir without indexing icon libraries."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.verbose = -1 if args.quiet else args.verbose
        self.rc = load_rc()
        self.local_dir = (
            args.local_dir if args.local_dir is not None else self.rc.local_dir
        )
        if self.local_dir is None:
            self.local_dir = "icons"
        self.project_dir = self.rc.project_dir or Path.cwd()
        self.local_root = (self.project_dir / self.local_dir).resolve()

    def require_local_root(self) -> Path:
        if not self.local_root.is_dir():
            raise FileNotFoundError(
                f"local assets directory not found: {self.local_root}"
            )
        return self.local_root


def icon_stem(name: str) -> str:
    """Normalize a CLI icon name to a filename stem (strip a trailing image ext)."""
    p = Path(name)
    if p.suffix.lower() in IMAGE_EXTS:
        return p.stem
    return name


def find_local_files(root: Path, name: str) -> list[Path]:
    """Find image files under *root* whose stem equals *name*."""
    stem = icon_stem(name)
    out: list[Path] = []
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        if path.suffix.lower() not in IMAGE_EXTS and path.suffix:
            continue
        # Allow extensionless stems (schema ``m``) and normal image files.
        if path.suffix.lower() in IMAGE_EXTS or path.suffix == "":
            if path.stem == stem:
                out.append(path)
    return out


def with_stem(path: Path, new_stem: str) -> Path:
    return path.with_name(new_stem + path.suffix)


def replace_size_format_dirs(
    rel: Path,
    *,
    size: str | None = None,
    fmt: str | None = None,
) -> Path:
    """Rewrite size/format directory segments in a path relative to local-root."""
    parts = list(rel.parts[:-1])
    name = rel.name
    stem = Path(name).stem
    cur_ext = Path(name).suffix.lstrip(".").lower()
    if cur_ext == "jpeg":
        cur_ext = "jpg"

    new_fmt = fmt.lower().lstrip(".") if fmt else cur_ext
    if new_fmt == "jpeg":
        new_fmt = "jpg"

    if fmt:
        replaced = False
        for i, part in enumerate(parts):
            if part.lower() in _FORMAT_PARTS:
                parts[i] = new_fmt
                replaced = True
                break
        name = f"{stem}.{new_fmt}"
        if not replaced and new_fmt != cur_ext:
            # Keep file in place; only extension changes unless a format dir exists.
            pass

    if size:
        norm = normalize_size(size)
        replaced = False
        for i, part in enumerate(parts):
            if SIZE_RE.match(part) or BARE_SIZE_RE.match(part):
                parts[i] = norm
                replaced = True
                break
        if not replaced:
            parts.append(norm)

    if fmt and not any(p.lower() in _FORMAT_PARTS for p in parts):
        name = f"{stem}.{new_fmt}"

    return Path(*parts, name) if parts else Path(name)
