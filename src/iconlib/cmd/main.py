# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib CLI entrypoint and shared options."""

from __future__ import annotations

import argparse
import sys
from typing import TextIO

from ..ilcommon import init_i18n
from . import (
    browse,
    copy,
    delete,
    index,
    info,
    libraries,
    ln,
    make,
    pull,
    push,
    rename,
    search,
    which,
)

_COMMAND_MODULES = (
    search,
    which,
    info,
    pull,
    push,
    browse,
    libraries,
    index,
    delete,
    rename,
    copy,
    ln,
    make,
)


def usage_epilog() -> str:
    return _(
        "Commands:\n"
        "  search [pattern]   list matching icon names\n"
        "  which [-a] name    print icon path(s)\n"
        "  info name          print icon metadata\n"
        "  libraries          list discovered icon libraries\n"
        "  pull [pattern]     copy icons into the project\n"
        "  push [pattern]     upload icons (not implemented)\n"
        "  browse [pattern]   open themestylebrowser\n"
        "  index              generate web preview and/or FAISS index\n"
        "  delete name...     remove local icon files\n"
        "  rename old new     rename local icon files\n"
        "  copy from to       copy local icon files\n"
        "  ln [-sf] tgt name  link local icon files\n"
        "  make [-s SIZE] [-F FMT] name...  derive local variants\n"
        "\n"
        "Pattern: empty=all, exact name, glob, or /regex\n"
        "Plain English words also match synonyms/inflections (scored).\n"
        "Local commands operate under project-dir/local-dir (default: icons/).\n"
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
    for mod in _COMMAND_MODULES:
        mod.register(sub)
    return p


def print_version(out: TextIO) -> None:
    from .. import __version__

    out.write(f"iconlib {__version__}\n")
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    init_i18n(argv[0])

    parser = build_parser()
    cmds = {
        "search",
        "which",
        "info",
        "pull",
        "push",
        "browse",
        "index",
        "libraries",
        "ls",
        "delete",
        "rename",
        "copy",
        "ln",
        "make",
    }
    if "--version" in argv[1:] and not any(a in cmds for a in argv[1:]):
        print_version(sys.stdout)
        return 0

    args = parser.parse_args(argv[1:])
    if args.version:
        print_version(sys.stdout)
        return 0
    if not args.cmd:
        parser.print_help()
        return 0

    return args._run(args)
