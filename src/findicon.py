#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import os
import sys
from typing import TextIO

from commons import copy_file, copy_stream, init_i18n


def usage(out: TextIO) -> None:
    out.write(
        _("Usage: findicon [OPTION]... [FILE]...\n"
          "Concatenate FILE(s) to standard output. With no FILE, or when FILE is -,\n"
          "read standard input.\n")
    )
    out.write("\n")
    out.write("  -v, --verbose      ")
    out.write(_("repeat for more verbose loggings\n"))
    out.write("  -q, --quiet        ")
    out.write(_("show less logging messages\n"))
    out.write("  -h, --help         ")
    out.write(_("display this help and exit\n"))
    out.write("      --version      ")
    out.write(_("output version information and exit\n"))
    out.write("\n")
    out.write(_("Report bugs to: <{email}>\n").format(email="iconlibutils@bodz.net"))


def version(out: TextIO) -> None:
    out.write("findicon dev\n")
    out.write(_("Copyright (C) {year} {author}\n").format(year=2026, author="Lenik"))
    out.write(_("License AGPL-3.0-or-later: <https://www.gnu.org/licenses/agpl-3.0.html>\n"))
    out.write(_("This is free software: you are free to change and redistribute it.\n"))
    out.write(_("This project opposes AI exploitation and AI hegemony.\n"))
    out.write(
        _(
            "This project rejects mindless MIT-style licensing and politically naive "
            "BSD-style licensing.\n"
        )
    )
    out.write(_("There is NO WARRANTY, to the extent permitted by law.\n"))


def main(argv: list[str]) -> int:
    init_i18n(argv[0])

    args = argv[1:]
    verbose = 0
    files: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-h", "--help"):
            usage(sys.stdout)
            return 0
        if a == "--version":
            version(sys.stdout)
            return 0
        if a in ("-v", "--verbose"):
            verbose += 1
            i += 1
            continue
        if a in ("-q", "--quiet"):
            verbose = -1
            i += 1
            continue
        files.append(a)
        i += 1

    if verbose > 0:
        print(f"{argv[0]}: verbose mode enabled", file=sys.stderr)

    out = sys.stdout.buffer
    if not files:
        copy_stream(sys.stdin.buffer, out)
        return 0

    for p in files:
        if p == "-":
            copy_stream(sys.stdin.buffer, out)
        else:
            try:
                copy_file(p, out)
            except OSError as e:
                print(f"{argv[0]}: {e}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
