# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib browse — open themestylebrowser on a library."""

from __future__ import annotations

import argparse
import os
import shutil
import sys

from ..autoindex import compile_pattern
from .context import Context


def register(sub: argparse._SubParsersAction) -> None:
    bp = sub.add_parser("browse", help=_("browse with themestylebrowser"))
    bp.add_argument("pattern", nargs="?", default="")
    bp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = Context(args)
    tsb = shutil.which("themestylebrowser")
    if not tsb:
        print("iconlib: themestylebrowser not found in PATH", file=sys.stderr)
        return 1

    pattern = ctx.args.pattern
    libs = list(ctx.libs)
    if pattern:
        pred = compile_pattern(pattern)
        by_name = [lib for lib in libs if pred(lib.name)]
        if by_name:
            libs = by_name
        else:
            groups = ctx.matched_groups(pattern)
            keep = {a.library for g in groups for a in g.assets}
            libs = [lib for lib in libs if lib.name in keep]

    browsable = [lib for lib in libs if (lib.path / ".themestyles").is_file()]
    skipped = [lib for lib in libs if lib not in browsable]
    for lib in skipped:
        print(
            f"iconlib: skip {lib.name}: no .themestyles under {lib.path}",
            file=sys.stderr,
        )
    if not browsable:
        print("iconlib: no browsable libraries", file=sys.stderr)
        return 1

    if len(browsable) > 1:
        print(
            "iconlib: opening first library; also browsable: "
            + ", ".join(lib.name for lib in browsable[1:]),
            file=sys.stderr,
        )
    target = browsable[0].path
    if ctx.verbose > 0:
        print(f"iconlib: exec {tsb} {target}", file=sys.stderr)
    os.execv(tsb, [tsb, str(target)])
    return 1  # unreachable
