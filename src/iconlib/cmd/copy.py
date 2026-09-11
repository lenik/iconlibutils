# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib copy — copy local icon files to a new name."""

from __future__ import annotations

import argparse
import shutil
import sys

from .project import ProjectContext, find_local_files, icon_stem, with_stem


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("copy", help=_("copy local icon files to a new name"))
    sp.add_argument("source", metavar="FROM", help=_("existing icon name"))
    sp.add_argument("dest", metavar="TO", help=_("new icon name"))
    sp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = ProjectContext(args)
    try:
        root = ctx.require_local_root()
    except FileNotFoundError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    src_name = icon_stem(args.source)
    dst_name = icon_stem(args.dest)
    if src_name == dst_name:
        print("iconlib: FROM and TO are the same", file=sys.stderr)
        return 1

    paths = find_local_files(root, src_name)
    if not paths:
        print(f"iconlib: {src_name}: not found under {root}", file=sys.stderr)
        return 1

    if find_local_files(root, dst_name):
        print(f"iconlib: {dst_name}: already exists under {root}", file=sys.stderr)
        return 1

    count = 0
    for src in paths:
        dest = with_stem(src, dst_name)
        if dest.exists() or dest.is_symlink():
            print(f"iconlib: refuse to overwrite {dest}", file=sys.stderr)
            return 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest, follow_symlinks=False)
        count += 1
        if ctx.verbose > 0:
            print(f"iconlib: {src} -> {dest}", file=sys.stderr)

    if ctx.verbose >= 0:
        print(
            _("Copied {n} local file(s) {src} → {dst}").format(
                n=count, src=src_name, dst=dst_name
            )
        )
    return 0
