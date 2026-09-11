# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib which — print icon path(s) for a name."""

from __future__ import annotations

import argparse
import sys

from ..autoindex import filter_groups, prefer_asset
from .context import Context


def register(sub: argparse._SubParsersAction) -> None:
    wp = sub.add_parser("which", help=_("print icon paths for the name"))
    wp.add_argument(
        "-a",
        action="store_true",
        dest="all_paths",
        help=_("print all matching paths"),
    )
    wp.add_argument("name")
    wp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = Context(args)
    name = ctx.args.name
    groups = filter_groups(ctx.groups, name, ctx.lib_names)
    groups = [g for g in groups if g.name == name]
    if not groups:
        print(f"iconlib: {name}: not found", file=sys.stderr)
        return 1
    assets = groups[0].assets
    if ctx.args.all_paths:
        for a in sorted(assets, key=lambda x: (x.library, x.orig)):
            print(a.path)
        return 0
    pref = prefer_asset(assets)
    if pref is None:
        print(f"iconlib: {name}: not found", file=sys.stderr)
        return 1
    print(pref.path)
    return 0
