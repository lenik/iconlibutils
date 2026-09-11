#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""findicon — shortcut for ``iconlib search``."""

from __future__ import annotations

import sys

from iconlib.cli import main as iconlib_main


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    rest = argv[1:]
    if rest == ["--version"]:
        return iconlib_main(["iconlib", "--version"])
    return iconlib_main(["iconlib", "search", *rest])


if __name__ == "__main__":
    raise SystemExit(main())
