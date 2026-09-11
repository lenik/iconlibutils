# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib search — find icons matching a query."""

from __future__ import annotations

import argparse
import sys


def register(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("search", help=_("find icons matching the query"))
    g = sp.add_mutually_exclusive_group()
    g.add_argument(
        "-l",
        "--long",
        action="store_true",
        help=_("long format including score"),
    )
    g.add_argument(
        "-1",
        "--names",
        action="store_true",
        help=_("output names only (default)"),
    )
    sp.add_argument("pattern", nargs="?", default="")
    sp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    # Heavy imports deferred so ``iconlib -h`` stays fast.
    from ..autoindex import IconGroup, prefer_asset, search_groups
    from ..faissidx import find_faiss_dir, query_libraries_faiss
    from ..semantic import is_plain_query
    from .context import Context

    ctx = Context(args)
    long_fmt = bool(getattr(ctx.args, "long", False))
    pattern = ctx.args.pattern

    # Baseline: literal / WordNet+inflection semantic ranking.
    ranked = search_groups(ctx.groups, pattern, ctx.lib_names)
    by_name: dict[str, tuple[float, object]] = {
        g.name: (score, g) for score, g in ranked
    }

    # Optional FAISS enrichment when indexes exist; otherwise keep semantics only.
    if pattern and is_plain_query(pattern):
        has_faiss = any(find_faiss_dir(lib.path, lib.meta_path) for lib in ctx.libs)
        if has_faiss:
            try:
                faiss_hits = query_libraries_faiss(
                    ctx.libs, pattern, verbose=ctx.verbose
                )
            except RuntimeError as e:
                if ctx.verbose >= 0:
                    print(
                        f"iconlib: FAISS unavailable, using WordNet/semantic search:\n{e}",
                        file=sys.stderr,
                    )
                faiss_hits = []
            for score, lib_name, icon_name in faiss_hits:
                g = ctx.groups.get(icon_name)
                if g is None:
                    continue
                assets = [a for a in g.assets if a.library == lib_name]
                if not assets:
                    assets = [a for a in g.assets if a.library in ctx.lib_names]
                if not assets:
                    continue
                ng = IconGroup(name=icon_name, assets=assets)
                prev = by_name.get(icon_name)
                if prev is None or score > prev[0]:
                    by_name[icon_name] = (score, ng)
        elif ctx.verbose > 0:
            print(
                "iconlib: no FAISS index; using WordNet/semantic search",
                file=sys.stderr,
            )

    results = sorted(by_name.values(), key=lambda x: (-x[0], x[1].name))
    for score, g in results:
        if long_fmt:
            by_lib: dict[str, list] = {}
            for a in g.assets:
                by_lib.setdefault(a.library, []).append(a)
            for lib_name in sorted(by_lib):
                assets = by_lib[lib_name]
                formats = ",".join(sorted({a.format for a in assets}))
                pref = prefer_asset(assets)
                orig = pref.orig if pref else assets[0].orig
                print(f"{score:.1f}\t{lib_name}\t{g.name}\t{orig}\t{formats}")
        else:
            print(g.name)
    return 0
