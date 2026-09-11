# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib push — upload icons to a remote library (stub)."""

from __future__ import annotations

import argparse
import sys


def register(sub: argparse._SubParsersAction) -> None:
    up = sub.add_parser("push", help=_("upload icons to a remote library"))
    up.add_argument("pattern", nargs="?", default="")
    up.set_defaults(_run=run)


def run(_args: argparse.Namespace) -> int:
    print(
        "iconlib: push is not implemented yet (no remote protocol)",
        file=sys.stderr,
    )
    return 1
