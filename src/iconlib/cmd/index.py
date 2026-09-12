# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""iconlib index — web preview and/or FAISS index generation."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from ..faissidx import generate_faiss_index, parse_byte_size
from ..paths import load_project_library
from .context import Context


def default_template_dir() -> Path | None:
    """Resolve installed or source-tree index template directory."""
    from ..site import get_index_template_dir

    return get_index_template_dir()


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


def register(sub: argparse._SubParsersAction) -> None:
    xp = sub.add_parser(
        "index",
        help=_("generate web preview and/or FAISS index"),
    )
    xp.add_argument(
        "-w",
        "--web",
        action="store_true",
        help=_("create web preview (default when neither -w nor -F is given)"),
    )
    xp.add_argument(
        "-F",
        "--faiss",
        action="store_true",
        help=_("create FAISS index (faiss / faiss.map / faiss.json)"),
    )
    xp.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=_("overwrite existing outputs"),
    )
    xp.add_argument(
        "-u",
        "--upscale",
        default="300x300",
        metavar="SIZE",
        help=_("FAISS canvas size before CLIP (default: 300x300)"),
    )
    xp.add_argument(
        "-s",
        "--shard-size",
        default=None,
        metavar="SIZE",
        help=_(
            "approx. max raw FAISS shard size (e.g. 10M); "
            "0/omit = no sharding (or library.iconlib faiss_shard_size=)"
        ),
    )
    xp.add_argument(
        "-o",
        "--outdir",
        default=None,
        metavar="DIR",
        help=_(
            "web preview output directory "
            "(default: index/ with project library.iconlib, else .)"
        ),
    )
    xp.add_argument(
        "--name",
        dest="index_name",
        metavar="NAME",
        help=_("library id embedded in the web page (default: first -l or basename)"),
    )
    xp.add_argument(
        "--title",
        dest="index_title",
        default="",
        help=_("web preview display title"),
    )
    xp.add_argument(
        "--license",
        dest="index_license",
        default="see-upstream",
        help=_("license label shown in the web page"),
    )
    xp.add_argument(
        "--homepage",
        dest="index_homepage",
        default="#",
        help=_("homepage URL shown in the web page"),
    )
    xp.add_argument(
        "--icons-root",
        dest="icons_roots",
        action="append",
        default=[],
        metavar="DIR",
        help=_("icon root to scan (repeatable; default: selected library paths)"),
    )
    xp.add_argument(
        "--icons-url-prefix",
        default="..",
        help=_("URL prefix for SVG hrefs in the web preview (default: ..)"),
    )
    xp.add_argument(
        "--template",
        dest="index_template",
        metavar="DIR",
        help=_("web template directory (default: <pkgdatadir>/index)"),
    )
    xp.add_argument(
        "--max-icons",
        type=int,
        default=0,
        help=_("limit number of icons for web preview (0 = unlimited)"),
    )
    xp.set_defaults(_run=run)


def run(args: argparse.Namespace) -> int:
    do_web = bool(args.web)
    do_faiss = bool(args.faiss)
    if not do_web and not do_faiss:
        do_web = True

    project = Path.cwd().resolve()
    proj_lib = load_project_library(project)
    # Packaging tree: ``iconlib index -F`` builds both web (index/) and FAISS (.).
    if do_faiss and proj_lib is not None and not args.web:
        do_web = True

    roots = [Path(p).expanduser() for p in (args.icons_roots or [])]
    name = args.index_name or ""
    title = args.index_title or ""
    license_ = args.index_license
    homepage = args.index_homepage
    verbose = -1 if args.quiet else args.verbose
    icons_url_prefix = args.icons_url_prefix

    if not roots and proj_lib is not None and proj_lib.icons_roots:
        roots = [(project / rel).expanduser() for rel in proj_lib.icons_roots]
        if not name:
            name = proj_lib.name
        if not title:
            title = proj_lib.title or proj_lib.name
        if license_ == "see-upstream" and proj_lib.license:
            license_ = proj_lib.license
        if homepage == "#" and proj_lib.homepage:
            homepage = proj_lib.homepage

    if not roots:
        try:
            ctx = Context(args)
        except SystemExit as e:
            print(e, file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"iconlib: {e}", file=sys.stderr)
            return 1
        roots = [lib.path for lib in ctx.libs]
        if not name and ctx.libs:
            name = ctx.libs[0].name
            if not title:
                title = ctx.libs[0].title or name
            if license_ == "see-upstream" and ctx.libs[0].license:
                license_ = ctx.libs[0].license
            if homepage == "#" and ctx.libs[0].homepage:
                homepage = ctx.libs[0].homepage
        verbose = ctx.verbose

    if not roots:
        print(
            "iconlib: index requires -l LIBRARY, --icons-root DIR, "
            "or library.iconlib with icons_root=",
            file=sys.stderr,
        )
        return 1
    if not name:
        name = roots[0].name

    # Web → index/ in packaging trees; FAISS → package root (.).
    if args.outdir is not None:
        web_outdir = Path(args.outdir).expanduser()
        faiss_outdir = web_outdir
    elif proj_lib is not None:
        web_outdir = project / "index"
        faiss_outdir = project
    else:
        web_outdir = Path(".")
        faiss_outdir = web_outdir

    if icons_url_prefix == ".." and proj_lib is not None and len(roots) == 1:
        try:
            rel_root = roots[0].resolve().relative_to(project)
            icons_url_prefix = f"../{rel_root.as_posix()}"
        except ValueError:
            pass

    if do_web:
        web_outs = [
            web_outdir / "index.html",
            web_outdir / "icons.json",
            web_outdir / "style.css",
            web_outdir / "app.js",
        ]
        if not args.force and any(p.exists() for p in web_outs):
            print(
                "iconlib: web preview outputs exist (use -f/--force to overwrite)",
                file=sys.stderr,
            )
            return 1
        template = (
            Path(args.index_template) if args.index_template else default_template_dir()
        )
        try:
            count = generate_index(
                name=name,
                title=title or name,
                license_=license_,
                homepage=homepage,
                outdir=web_outdir,
                icons_roots=roots,
                template=template,
                icons_url_prefix=icons_url_prefix,
                max_icons=args.max_icons,
            )
        except (FileNotFoundError, ValueError) as e:
            print(f"iconlib: {e}", file=sys.stderr)
            return 1
        if verbose >= 0:
            print(f"iconlib: wrote web preview for {name}: {count} icons → {web_outdir}")

    if do_faiss:
        shard_raw = args.shard_size
        if shard_raw is None and proj_lib is not None:
            shard_raw = proj_lib.faiss_shard_size or None
        try:
            shard_size = parse_byte_size(shard_raw)
        except ValueError as e:
            print(f"iconlib: {e}", file=sys.stderr)
            return 1
        try:
            n = generate_faiss_index(
                icons_roots=roots,
                outdir=faiss_outdir,
                upscale=args.upscale,
                force=args.force,
                verbose=verbose,
                shard_size=shard_size,
            )
        except (FileExistsError, FileNotFoundError, ValueError, RuntimeError) as e:
            print(f"iconlib: {e}", file=sys.stderr)
            return 1
        if verbose >= 0:
            print(f"iconlib: wrote FAISS index for {n} icons → {faiss_outdir}")

    return 0
