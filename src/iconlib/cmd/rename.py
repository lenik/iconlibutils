# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib rename — rename local icon files."""

from __future__ import annotations

import argparse
import sys

from .project import ProjectContext, find_local_files, icon_stem, with_stem


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("rename", help=_("rename local icon files"))
    sp.add_argument("old", metavar="OLD", help=_("existing icon name"))
    sp.add_argument("new", metavar="NEW", help=_("new icon name"))
    sp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = ProjectContext(args)
    try:
        root = ctx.require_local_root()
    except FileNotFoundError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    old = icon_stem(args.old)
    new = icon_stem(args.new)
    if old == new:
        print("iconlib: OLD and NEW are the same", file=sys.stderr)
        return 1

    paths = find_local_files(root, old)
    if not paths:
        print(f"iconlib: {old}: not found under {root}", file=sys.stderr)
        return 1

    # Refuse if NEW already has any local files.
    if find_local_files(root, new):
        print(f"iconlib: {new}: already exists under {root}", file=sys.stderr)
        return 1

    count = 0
    for src in paths:
        dest = with_stem(src, new)
        if dest.exists() or dest.is_symlink():
            print(f"iconlib: refuse to overwrite {dest}", file=sys.stderr)
            return 1
        src.rename(dest)
        count += 1
        if ctx.verbose > 0:
            print(f"iconlib: {src} -> {dest}", file=sys.stderr)

    if ctx.verbose >= 0:
        print(_("Renamed {n} file(s) {old} → {new}").format(n=count, old=old, new=new))
    return 0
