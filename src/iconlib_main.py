#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Bindir wrapper for the iconlib CLI package."""

from __future__ import annotations

from iconlib.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
