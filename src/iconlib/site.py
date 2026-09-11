# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Runtime paths and version (Meson-substituted ``_config`` when installed)."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def _meson_config():
    try:
        from . import _config as c  # type: ignore[attr-defined]

        return c
    except ImportError:
        return None


def _repo_root() -> Path | None:
    """Return source checkout root when running from a work tree."""
    here = Path(__file__).resolve()
    # .../src/iconlib/site.py → parents[2] == repo
    repo = here.parents[2]
    if (repo / "meson.build").is_file() and (repo / "share" / "index").is_dir():
        return repo
    return None


@lru_cache(maxsize=1)
def get_version() -> str:
    c = _meson_config()
    ver = getattr(c, "VERSION", "") if c else ""
    if ver and ver != "@VERSION@":
        return ver
    repo = _repo_root()
    if repo is not None:
        vf = repo / "VERSION"
        if vf.is_file():
            return vf.read_text(encoding="utf-8").strip().lstrip("v")
    try:
        from importlib.metadata import version

        return version("iconlibutils")
    except Exception:
        pass
    return "0.0.0"


@lru_cache(maxsize=1)
def get_pkgdatadir() -> Path:
    env = os.environ.get("ICONLIBUTILS_PKGDATADIR", "").strip()
    if env:
        return Path(env).expanduser()
    c = _meson_config()
    raw = getattr(c, "PKGDATADIR", "") if c else ""
    if raw and not raw.startswith("@"):
        return Path(raw)
    repo = _repo_root()
    if repo is not None:
        # Source layout: share/index, share/… (installed as pkgdatadir/*).
        return repo / "share"
    return Path(sys.prefix) / "share" / "iconlibutils"


@lru_cache(maxsize=1)
def get_datadir() -> Path:
    env = os.environ.get("ICONLIBUTILS_DATADIR", "").strip()
    if env:
        return Path(env).expanduser()
    c = _meson_config()
    raw = getattr(c, "DATADIR", "") if c else ""
    if raw and not raw.startswith("@"):
        return Path(raw)
    repo = _repo_root()
    if repo is not None:
        return repo / "share"
    return Path(sys.prefix) / "share"


@lru_cache(maxsize=1)
def get_localedir() -> Path:
    env = os.environ.get("ICONLIBUTILS_LOCALEDIR", "").strip()
    if env:
        return Path(env).expanduser()
    c = _meson_config()
    raw = getattr(c, "LOCALEDIR", "") if c else ""
    if raw and not raw.startswith("@"):
        return Path(raw)
    return Path(sys.prefix) / "share" / "locale"


@lru_cache(maxsize=1)
def get_wordnet_dir() -> Path:
    env = os.environ.get("ICONLIBUTILS_WORDNET_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    c = _meson_config()
    raw = getattr(c, "WORDNET_DIR", "") if c else ""
    if raw and not raw.startswith("@"):
        return Path(raw)
    # wordnet-base installs here on Debian/Ubuntu regardless of prefix.
    return Path("/usr/share/wordnet")


def get_index_template_dir() -> Path | None:
    """Resolve web index template directory (pkgdatadir/index)."""
    candidates = [
        get_pkgdatadir() / "index",
    ]
    repo = _repo_root()
    if repo is not None:
        candidates.append(repo / "share" / "index")
    for p in candidates:
        if (p / "index.html.in").is_file():
            return p
    return None


def default_icon_datadir(name: str) -> Path:
    """Default on-disk path for an icons-<name> package."""
    return get_datadir() / f"icons-{name}"
