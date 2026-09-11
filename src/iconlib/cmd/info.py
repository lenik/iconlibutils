# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib info — print icon metadata."""

from __future__ import annotations

import argparse
import sys

from ..autoindex import filter_groups
from .context import Context


def register(sub: argparse._SubParsersAction) -> None:
    ip = sub.add_parser("info", help=_("print icon info"))
    ip.add_argument("name")
    ip.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    ctx = Context(args)
    name = ctx.args.name
    groups = [
        g for g in filter_groups(ctx.groups, name, ctx.lib_names) if g.name == name
    ]
    if not groups:
        print(f"iconlib: {name}: not found", file=sys.stderr)
        return 1
    g = groups[0]
    print(f"name: {g.name}")
    print(f"formats: {', '.join(g.formats())}")
    sizes = g.sizes()
    if sizes:
        print(f"sizes: {', '.join(sizes)}")
    libs = sorted({a.library for a in g.assets})
    print(f"libraries: {', '.join(libs)}")
    variants = sorted({a.variant for a in g.assets if a.variant})
    if variants:
        print(f"variants: {', '.join(variants)}")
    print("assets:")
    for a in sorted(g.assets, key=lambda x: (x.library, x.orig)):
        extra = []
        if a.variant:
            extra.append(a.variant)
        if a.size:
            extra.append(a.size)
        suffix = f" ({', '.join(extra)})" if extra else ""
        print(f"  {a.library}: {a.path}{suffix}")
    return 0
