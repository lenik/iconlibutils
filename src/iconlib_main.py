#!/usr/bin/python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Python entry for the iconlib CLI (invoked by the iconlib bash launcher)."""

from __future__ import annotations

from iconlib.cmd import main

if __name__ == "__main__":
    raise SystemExit(main())
