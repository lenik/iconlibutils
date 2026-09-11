# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib delete — remove local icon files by name."""

from __future__ import annotations

import argparse
import sys

from .project import ProjectContext, find_local_files, icon_stem


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("delete", help=_("delete local icon files by name"))
    sp.add_argument(
        "names",
        nargs="+",
        metavar="NAME",
        help=_("icon name(s) to remove from the local assets directory"),
    )
    sp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = ProjectContext(args)
    try:
        root = ctx.require_local_root()
    except FileNotFoundError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    removed = 0
    missing = 0
    for raw in args.names:
        name = icon_stem(raw)
        paths = find_local_files(root, name)
        if not paths:
            print(f"iconlib: {name}: not found under {root}", file=sys.stderr)
            missing += 1
            continue
        for path in paths:
            path.unlink()
            removed += 1
            if ctx.verbose > 0:
                print(f"iconlib: deleted {path}", file=sys.stderr)

    if removed == 0:
        return 1
    if ctx.verbose >= 0:
        print(_("Deleted {n} file(s) under {dir}").format(n=removed, dir=root))
    return 1 if missing else 0
