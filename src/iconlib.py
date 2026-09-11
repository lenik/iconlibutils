#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib — search, inspect, and pull icons from installed libraries."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import TextIO

from autoindex import (
    filter_assets,
    filter_groups,
    index_libraries,
    parse_size_args,
    prefer_asset,
    search_groups,
)
from ilcommon import init_i18n
from paths import env_path_files, load_libraries, resolve_library_names
from rc import load_rc
from schema import expand_dest


def usage_epilog() -> str:
    return _(
        "Commands:\n"
        "  search [pattern]   list matching icon names\n"
        "  which [-a] name    print icon path(s)\n"
        "  info name          print icon metadata\n"
        "  pull [pattern]     copy icons into the project\n"
        "  push [pattern]     upload icons (not implemented)\n"
        "  browse [pattern]   open themestylebrowser\n"
        "\n"
        "Pattern: empty=all, exact name, glob, or /regex\n"
        "Plain English words also match synonyms/inflections (scored).\n"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="iconlib",
        description=_("Search and manage icons from installed icon libraries."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=usage_epilog(),
    )
    p.add_argument(
        "-l",
        dest="libraries",
        action="append",
        default=[],
        metavar="LIBRARY",
        help=_("add/restrict icon library (repeatable; prefix match)"),
    )
    p.add_argument(
        "-d",
        "--local-dir",
        dest="local_dir",
        metavar="DIR",
        help=_("local assets directory for pull (relative to project-dir)"),
    )
    p.add_argument(
        "-s",
        "--schema",
        dest="schema",
        metavar="SCHEMA",
        help=_("pull path schema (e.g. n, l/f/n, l/v/n)"),
    )
    p.add_argument(
        "-m",
        "--map",
        dest="maps",
        action="append",
        default=[],
        metavar="NAME=DIR",
        help=_("map library name to local dirname"),
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=_("repeat for more verbose loggings"),
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help=_("show less logging messages"),
    )
    p.add_argument(
        "--version",
        action="store_true",
        help=_("output version information and exit"),
    )

    sub = p.add_subparsers(dest="cmd")

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

    wp = sub.add_parser("which", help=_("print icon paths for the name"))
    wp.add_argument(
        "-a",
        action="store_true",
        dest="all_paths",
        help=_("print all matching paths"),
    )
    wp.add_argument("name")

    ip = sub.add_parser("info", help=_("print icon info"))
    ip.add_argument("name")

    pp = sub.add_parser("pull", help=_("retrieve icons to the project"))
    pp.add_argument(
        "-F",
        "--format",
        dest="formats",
        action="append",
        default=[],
        metavar="FORMAT",
        help=_("add a format (repeatable); default all"),
    )
    pp.add_argument(
        "-S",
        "--size",
        dest="sizes",
        action="append",
        default=[],
        metavar="SIZE",
        help=_("add an image size or alias=size (repeatable)"),
    )
    pp.add_argument("pattern", nargs="?", default="")

    up = sub.add_parser("push", help=_("upload icons to a remote library"))
    up.add_argument("pattern", nargs="?", default="")

    bp = sub.add_parser("browse", help=_("browse with themestylebrowser"))
    bp.add_argument("pattern", nargs="?", default="")

    return p


def print_version(out: TextIO) -> None:
    out.write("iconlib 0.0.1\n")
    out.write(_("Copyright (C) {year} {author}\n").format(year=2026, author="Lenik"))
    out.write(
        _("License AGPL-3.0-or-later: <https://www.gnu.org/licenses/agpl-3.0.html>\n")
    )
    out.write(_("This is free software: you are free to change and redistribute it.\n"))
    out.write(_("This project opposes AI exploitation and AI hegemony.\n"))
    out.write(
        _(
            "This project rejects mindless MIT-style licensing and politically naive "
            "BSD-style licensing.\n"
        )
    )
    out.write(_("There is NO WARRANTY, to the extent permitted by law.\n"))


def parse_maps(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"-m expects NAME=DIR, got {item!r}")
        name, dirname = item.split("=", 1)
        out[name.strip()] = dirname.strip()
    return out


def merge_maps(rc_maps: dict[str, str], cli_maps: list[str]) -> dict[str, str]:
    merged = dict(rc_maps)
    merged.update(parse_maps(cli_maps))
    return merged


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.verbose = -1 if args.quiet else args.verbose
        self.rc = load_rc()

        cli_libs = list(args.libraries or [])
        rc_libs = list(self.rc.libraries)
        # CLI -l restricts/adds; if CLI provided any, use CLI list as selectors
        # plus we still need registry. Plan: rc -l are additional search path selectors
        # merged with CLI; if either set, filter to those.
        self.lib_specs = cli_libs + [x for x in rc_libs if x not in cli_libs]

        self.local_dir = (
            args.local_dir if args.local_dir is not None else self.rc.local_dir
        )
        if self.local_dir is None:
            self.local_dir = "icons"

        self.schema = args.schema if args.schema is not None else self.rc.schema
        if self.schema is None:
            self.schema = "n"

        self.maps = merge_maps(self.rc.maps, args.maps or [])
        self.project_dir = self.rc.project_dir or Path.cwd()

        self.registry = load_libraries(env_path_files())
        try:
            self.libs = resolve_library_names(
                self.registry, self.lib_specs if self.lib_specs else None
            )
        except KeyError as e:
            raise SystemExit(f"iconlib: {e}") from e

        if self.verbose > 0:
            for lib in self.libs:
                print(
                    f"iconlib: library {lib.name} ({lib.type}) -> {lib.path}",
                    file=sys.stderr,
                )

        self.groups = index_libraries(self.libs)
        self.lib_names = {lib.name for lib in self.libs}

    def matched_groups(self, pattern: str):
        return filter_groups(self.groups, pattern, self.lib_names)


def cmd_search(ctx: Context) -> int:
    long_fmt = bool(getattr(ctx.args, "long", False))
    ranked = search_groups(ctx.groups, ctx.args.pattern, ctx.lib_names)
    for score, g in ranked:
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


def cmd_which(ctx: Context) -> int:
    name = ctx.args.name
    groups = filter_groups(ctx.groups, name, ctx.lib_names)
    # exact name only for which
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


def cmd_info(ctx: Context) -> int:
    name = ctx.args.name
    groups = [g for g in filter_groups(ctx.groups, name, ctx.lib_names) if g.name == name]
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


def cmd_pull(ctx: Context) -> int:
    formats = {f.lower().lstrip(".") for f in (ctx.args.formats or [])} or None
    if formats:
        formats = {("jpg" if f == "jpeg" else f) for f in formats}
    size_wanted, size_aliases = parse_size_args(ctx.args.sizes or [])
    sizes = size_wanted or None

    groups = ctx.matched_groups(ctx.args.pattern)
    if not groups:
        print("iconlib: no icons matched", file=sys.stderr)
        return 1

    dest_root = ctx.project_dir / ctx.local_dir
    copied = 0
    for g in groups:
        if formats or sizes:
            assets = filter_assets(g.assets, formats, sizes)
        else:
            assets = list(g.assets)
        if not assets:
            continue

        seen: set[tuple] = set()
        for a in sorted(
            assets, key=lambda x: (x.library, x.format, x.size or "", x.orig)
        ):
            key = (a.library, a.format, a.size, a.variant, a.name)
            if key in seen:
                continue
            seen.add(key)
            rel = expand_dest(
                a, ctx.schema, maps=ctx.maps, size_aliases=size_aliases or None
            )
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.path, dest)
            copied += 1
            if ctx.verbose > 0:
                print(f"iconlib: {a.path} -> {dest}", file=sys.stderr)

    if copied == 0:
        print("iconlib: no assets copied", file=sys.stderr)
        return 1
    if ctx.verbose >= 0:
        print(_("Copied {n} file(s) into {dir}").format(n=copied, dir=dest_root))
    return 0


def cmd_push(_ctx: Context) -> int:
    print(
        "iconlib: push is not implemented yet (no remote protocol)",
        file=sys.stderr,
    )
    return 1


def cmd_browse(ctx: Context) -> int:
    tsb = shutil.which("themestylebrowser")
    if not tsb:
        print("iconlib: themestylebrowser not found in PATH", file=sys.stderr)
        return 1

    # Filter libraries by pattern against library names (and optionally icon names).
    pattern = ctx.args.pattern
    libs = list(ctx.libs)
    if pattern:
        from autoindex import compile_pattern

        pred = compile_pattern(pattern)
        # Prefer matching library names; if none, libraries that contain matching icons
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

    # themestylebrowser takes a single librarydir; open the first, mention others.
    if len(browsable) > 1:
        print(
            "iconlib: opening first library; also browsable: "
            + ", ".join(lib.name for lib in browsable[1:]),
            file=sys.stderr,
        )
    target = browsable[0].path
    if ctx.verbose > 0:
        print(f"iconlib: exec {tsb} {target}", file=sys.stderr)
    os_exec = __import__("os").execv
    os_exec(tsb, [tsb, str(target)])
    return 1  # unreachable


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    init_i18n(argv[0])

    parser = build_parser()
    # Pre-handle --version before required subcommand
    if "--version" in argv[1:] and not any(
        a in {"search", "which", "info", "pull", "push", "browse"} for a in argv[1:]
    ):
        print_version(sys.stdout)
        return 0

    args = parser.parse_args(argv[1:])
    if args.version:
        print_version(sys.stdout)
        return 0
    if not args.cmd:
        parser.print_help()
        return 0

    try:
        ctx = Context(args)
    except ValueError as e:
        print(f"iconlib: {e}", file=sys.stderr)
        return 1

    handlers = {
        "search": cmd_search,
        "which": cmd_which,
        "info": cmd_info,
        "pull": cmd_pull,
        "push": cmd_push,
        "browse": cmd_browse,
    }
    return handlers[args.cmd](ctx)


if __name__ == "__main__":
    raise SystemExit(main())
