#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Discover and parse .iconlibrc project config."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RcOptions:
    libraries: list[str] = field(default_factory=list)
    local_dir: str | None = None
    schema: str | None = None
    maps: dict[str, str] = field(default_factory=dict)
    project_dir: Path | None = None
    rc_path: Path | None = None


def find_iconlibrc(start: Path | None = None) -> Path | None:
    """Walk from start (default cwd) toward filesystem root for .iconlibrc."""
    cur = (start or Path.cwd()).resolve()
    while True:
        candidate = cur / ".iconlibrc"
        if candidate.is_file():
            return candidate
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def parse_rc_text(text: str, source: str = ".iconlibrc") -> RcOptions:
    opts = RcOptions()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        flag = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        def need_arg() -> str:
            if arg is None:
                raise ValueError(f"{source}:{lineno}: {flag} requires an argument")
            return arg

        if flag in ("-l", "--library"):
            opts.libraries.append(need_arg())
        elif flag in ("-d", "--local-dir"):
            opts.local_dir = need_arg()
        elif flag in ("-s", "--schema"):
            opts.schema = need_arg()
        elif flag in ("-m", "--map"):
            mapping = need_arg()
            if "=" not in mapping:
                raise ValueError(f"{source}:{lineno}: -m expects NAME=DIR")
            name, dirname = mapping.split("=", 1)
            opts.maps[name.strip()] = dirname.strip()
        else:
            raise ValueError(f"{source}:{lineno}: unknown option {flag!r}")
    return opts


def load_rc(start: Path | None = None) -> RcOptions:
    path = find_iconlibrc(start)
    if path is None:
        return RcOptions()
    opts = parse_rc_text(path.read_text(encoding="utf-8", errors="replace"), str(path))
    opts.rc_path = path
    opts.project_dir = path.parent
    return opts
