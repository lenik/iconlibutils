# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib — search and manage icons from installed libraries."""

from __future__ import annotations

__all__ = ["__version__"]


def __getattr__(name: str):
    if name == "__version__":
        from .site import get_version

        return get_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
