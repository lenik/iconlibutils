# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib ln — link local icon files under a new name."""

from __future__ import annotations

import argparse
import os
import sys

from .project import ProjectContext, find_local_files, icon_stem, with_stem


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("ln", help=_("link local icon files under a new name"))
    sp.add_argument(
        "-s",
        "--symbolic",
        action="store_true",
        help=_("make symbolic links instead of hard links"),
    )
    sp.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=_("remove existing destination files"),
    )
    sp.add_argument("target", metavar="TARGET", help=_("existing icon name"))
    sp.add_argument("link", metavar="NAME", help=_("new link name"))
    sp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = ProjectContext(args)
    try:
        root = ctx.require_local_root()
    except FileNotFoundError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    target = icon_stem(args.target)
    link = icon_stem(args.link)
    if target == link:
        print("iconlib: TARGET and NAME are the same", file=sys.stderr)
        return 1

    paths = find_local_files(root, target)
    if not paths:
        print(f"iconlib: {target}: not found under {root}", file=sys.stderr)
        return 1

    if not args.force and find_local_files(root, link):
        print(f"iconlib: {link}: already exists under {root}", file=sys.stderr)
        return 1

    count = 0
    for src in paths:
        dest = with_stem(src, link)
        if dest.exists() or dest.is_symlink():
            if not args.force:
                print(f"iconlib: refuse to overwrite {dest}", file=sys.stderr)
                return 1
            dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if args.symbolic:
                os.symlink(src.name if dest.parent == src.parent else src, dest)
            else:
                os.link(src, dest)
        except OSError as e:
            print(f"iconlib: {dest}: {e}", file=sys.stderr)
            return 1
        count += 1
        if ctx.verbose > 0:
            kind = "symlink" if args.symbolic else "hardlink"
            print(f"iconlib: {kind} {dest} -> {src}", file=sys.stderr)

    if ctx.verbose >= 0:
        print(
            _("Linked {n} local file(s) {target} → {link}").format(
                n=count, target=target, link=link
            )
        )
    return 0
