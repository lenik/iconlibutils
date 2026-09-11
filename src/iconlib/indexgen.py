#!/usr/bin/env python3
# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Generate parameterized icon preview index pages (iconlib index)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def default_template_dir() -> Path | None:
    """Resolve installed or source-tree index template directory."""
    here = Path(__file__).resolve()
    candidates = [
        Path("/usr/share/iconlibutils/index"),
        Path("/usr/local/share/iconlibutils/index"),
        # src/iconlib/indexgen.py → repo/share/index
        here.parents[2] / "share" / "index",
        here.parent / "share" / "index",
    ]
    for p in candidates:
        if (p / "index.html.in").is_file():
            return p
    return None


def iter_svgs(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.svg")))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out


def rel_href(svg: Path, roots: list[Path], url_prefix: str) -> tuple[str, str]:
    name = svg.stem
    for root in roots:
        try:
            rel = svg.resolve().relative_to(root.resolve())
            href = f"{url_prefix.rstrip('/')}/{rel.as_posix()}"
            return name, href
        except ValueError:
            continue
    return name, f"{url_prefix.rstrip('/')}/{svg.name}"


def generate_index(
    *,
    name: str,
    outdir: Path,
    icons_roots: list[Path],
    template: Path | None = None,
    title: str = "",
    license_: str = "see-upstream",
    homepage: str = "#",
    icons_url_prefix: str = "..",
    max_icons: int = 0,
) -> int:
    """Write preview page + icons.json. Returns icon count."""
    tmpl = template or default_template_dir()
    if tmpl is None or not (tmpl / "index.html.in").is_file():
        raise FileNotFoundError(
            "index template not found; install iconlibutils or pass --template"
        )
    if not icons_roots:
        raise ValueError("at least one icons root is required")

    outdir.mkdir(parents=True, exist_ok=True)
    svgs = iter_svgs(icons_roots)
    if max_icons and len(svgs) > max_icons:
        svgs = svgs[:max_icons]

    icons = []
    for svg in svgs:
        iname, href = rel_href(svg, icons_roots, icons_url_prefix)
        icons.append({"name": iname, "path": href, "href": href})

    display = title or name
    html = (tmpl / "index.html.in").read_text(encoding="utf-8")
    for key, val in {
        "@LIB_NAME@": name,
        "@LIB_TITLE@": display,
        "@LIB_LICENSE@": license_,
        "@LIB_HOMEPAGE@": homepage,
        "@LIB_COUNT@": str(len(icons)),
    }.items():
        html = html.replace(key, val)
    (outdir / "index.html").write_text(html, encoding="utf-8")
    (outdir / "icons.json").write_text(
        json.dumps(
            {"name": name, "count": len(icons), "icons": icons},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for static in ("style.css", "app.js"):
        src = tmpl / static
        if src.is_file():
            shutil.copy2(src, outdir / static)
    return len(icons)
