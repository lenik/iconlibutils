#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Shared helpers for iconlibutils CLIs (i18n and small utilities).

from __future__ import annotations

import gettext
import locale
import os
from pathlib import Path
from typing import BinaryIO

TEXT_DOMAIN = "iconlibutils"


def init_i18n(argv0: str) -> gettext.NullTranslations:
    locale.setlocale(locale.LC_ALL, "")

    localedir = os.environ.get("ICONLIBUTILS_LOCALEDIR")
    if not localedir and "/" in argv0:
        build_po = Path(argv0).resolve().parent / "po"
        if build_po.is_dir():
            localedir = str(build_po)
    if not localedir:
        try:
            from .site import get_localedir

            localedir = str(get_localedir())
        except Exception:
            localedir = None

    trans = gettext.translation(TEXT_DOMAIN, localedir=localedir, fallback=True)
    trans.install()
    return trans


def copy_stream(src: BinaryIO, dst: BinaryIO) -> None:
    while True:
        chunk = src.read(8192)
        if not chunk:
            return
        dst.write(chunk)
        dst.flush()


def copy_file(path: str, out: BinaryIO) -> None:
    with open(path, "rb") as fh:
        copy_stream(fh, out)
