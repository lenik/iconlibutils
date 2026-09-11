# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Runtime context shared by library-aware commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..autoindex import filter_groups, index_libraries
from ..paths import load_libraries, resolve_library_names
from ..rc import load_rc


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
        # CLI -l restricts/adds; rc -l are additional selectors merged with CLI.
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

        self.registry = load_libraries()
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
