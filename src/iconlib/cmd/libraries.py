# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib libraries — list discovered icon libraries."""

from __future__ import annotations

import argparse
import sys

from ..paths import load_libraries, resolve_library_names


def register(sub: argparse._SubParsersAction) -> None:
    lp = sub.add_parser(
        "libraries",
        aliases=["ls"],
        help=_("list discovered icon libraries"),
    )
    lp.add_argument(
        "-l",
        "--long",
        action="store_true",
        help=_("show path, title, license, homepage"),
    )
    lp.add_argument(
        "-1",
        "--names",
        action="store_true",
        help=_("print library names only"),
    )
    lp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    registry = load_libraries()
    try:
        libs = resolve_library_names(
            registry, list(args.libraries) if args.libraries else None
        )
    except KeyError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    if not libs:
        if not getattr(args, "quiet", False):
            print("iconlib: no libraries discovered", file=sys.stderr)
        return 1

    for lib in libs:
        if getattr(args, "names", False):
            print(lib.name)
            continue
        if getattr(args, "long", False):
            title = lib.title or lib.name
            license_ = lib.license or "-"
            home = lib.homepage or "-"
            print(f"{lib.name}\t{lib.path}\t{title}\t{license_}\t{home}")
        else:
            exists = "ok" if lib.path.is_dir() else "missing"
            print(f"{lib.name}\t{lib.path}\t{exists}")
    return 0
