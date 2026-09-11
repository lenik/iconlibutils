# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build FAISS indexes from icon images + filename text via CLIP."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_SIZE = 224
FAISS_INDEX = "faiss.index"
FAISS_MAP = "faiss.map"
FAISS_JSON = "faiss.json"

_FILENAME_SEP_RE = re.compile(r"[_\-./\\+|]+")


def clip_download_help() -> str:
    """User-facing instructions to fetch the CLIP weights with hfd."""
    home_model = Path.home() / "models" / "clip-vit-base-patch32"
    return (
        "CLIP model not available for FAISS indexing/search.\n"
        "\n"
        "Download it first with hfd (Hugging Face Downloader), using the China\n"
        "mirror if needed (see ~/.bashrc.d/llm.sh):\n"
        "\n"
        "  export HF_ENDPOINT=https://hf-mirror.com\n"
        f"  mkdir -p {home_model.parent}\n"
        f"  hfd {CLIP_MODEL_ID} --local-dir {home_model}\n"
        "\n"
        "Or point ICONLIB_CLIP_MODEL at an existing local checkout:\n"
        "\n"
        f"  export ICONLIB_CLIP_MODEL={home_model}\n"
        "\n"
        "hfd usage:\n"
        "  hfd <REPO_ID> [--local-dir DIR] [--exclude PATTERN...] [-x N] [-j N]\n"
        "  hfd --help\n"
        "\n"
        f"Example:\n"
        f"  hfd {CLIP_MODEL_ID} --local-dir {home_model} -x 4 -j 4\n"
    )


def local_clip_model() -> Path | None:
    """Return a usable local CLIP directory, or None if not downloaded."""
    import os

    env = os.environ.get("ICONLIB_CLIP_MODEL", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    home = Path.home()
    candidates.extend(
        [
            home / "models" / "clip-vit-base-patch32",
            home / "models" / "openai" / "clip-vit-base-patch32",
        ]
    )
    for p in candidates:
        if (p / "config.json").is_file() and (
            (p / "pytorch_model.bin").is_file()
            or (p / "model.safetensors").is_file()
        ):
            return p
    return None


def require_clip_model() -> Path:
    """Require a local CLIP model; raise RuntimeError with hfd help if missing."""
    found = local_clip_model()
    if found is not None:
        return found
    raise RuntimeError(clip_download_help())


def resolve_clip_model() -> str:
    """
    Prefer a local CLIP checkout (e.g. via ``hfd``).

    Raises RuntimeError with download instructions when no local model exists
    (hub id alone is not enough — weights must be downloaded first).
    """
    return str(require_clip_model())


def parse_upscale(size: str) -> tuple[int, int]:
    """Parse SIZE as N or NxN / N×N into (width, height)."""
    raw = size.strip().lower().replace("×", "x")
    if "x" in raw:
        a, b = raw.split("x", 1)
        return int(a), int(b)
    n = int(raw)
    return n, n


def filename_to_text(path: Path) -> str:
    """Convert icon filename stem into a CLIP text phrase."""
    stem = path.stem
    text = _FILENAME_SEP_RE.sub(" ", stem)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or stem


def _rasterize_svg(path: Path, out_png: Path, size: tuple[int, int]) -> None:
    w, h = size
    # Render larger then fit on white canvas; rsvg keeps aspect with zoom.
    cmd = [
        "rsvg-convert",
        f"--width={w}",
        f"--height={h}",
        "--keep-aspect-ratio",
        "--background-color=white",
        "-o",
        str(out_png),
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def load_icon_rgb(path: Path, canvas_size: tuple[int, int]):
    """Load icon onto a white RGB canvas, preserving aspect ratio."""
    from PIL import Image

    w, h = canvas_size
    suffix = path.suffix.lower()
    if suffix == ".svg":
        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "icon.png"
            try:
                _rasterize_svg(path, png, canvas_size)
            except FileNotFoundError as e:
                raise RuntimeError(
                    "rsvg-convert not found; install librsvg2-bin for SVG FAISS indexing"
                ) from e
            except subprocess.CalledProcessError as e:
                err = (e.stderr or b"").decode("utf-8", "replace").strip()
                raise RuntimeError(f"SVG rasterize failed for {path}: {err}") from e
            img = Image.open(png).convert("RGBA")
    else:
        img = Image.open(path).convert("RGBA")

    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    img.thumbnail((w, h), Image.Resampling.LANCZOS)
    x = (w - img.width) // 2
    y = (h - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def _require_deps():
    missing = []
    try:
        import faiss  # noqa: F401
    except ImportError:
        missing.append("faiss (python3-faiss)")
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("PIL (python3-pil)")
    try:
        import torch  # noqa: F401
        from transformers import CLIPModel, CLIPProcessor  # noqa: F401
    except ImportError:
        missing.append("torch + transformers (CLIP)")
    if missing:
        raise RuntimeError(
            "FAISS indexing requires: " + ", ".join(missing)
        )


class ClipEncoder:
    """Lazy CLIP image/text encoder (224×224 ViT-B/32)."""

    def __init__(self, model_id: str | None = None) -> None:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        model_id = model_id or resolve_clip_model()
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self.processor = CLIPProcessor.from_pretrained(model_id)
            self.model = CLIPModel.from_pretrained(model_id).to(self.device)
        except Exception as e:
            raise RuntimeError(
                f"failed to load CLIP model {model_id!r}: {e}"
            ) from e
        self.model.eval()

    def encode_image(self, image) -> list[float]:
        torch = self.torch
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.get_image_features(**inputs)
            feats = out.pooler_output if hasattr(out, "pooler_output") else out
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats[0].detach().cpu().float().numpy()

    def encode_text(self, text: str):
        torch = self.torch
        inputs = self.processor(
            text=[text], return_tensors="pt", padding=True, truncation=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.get_text_features(**inputs)
            feats = out.pooler_output if hasattr(out, "pooler_output") else out
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats[0].detach().cpu().float().numpy()


def iter_icon_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                files.append(p)
    seen: set[Path] = set()
    out: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out


def generate_faiss_index(
    *,
    icons_roots: list[Path],
    outdir: Path,
    upscale: str = "300x300",
    force: bool = False,
    verbose: int = 0,
) -> int:
    """
    Write faiss.index, faiss.map (id TAB path), faiss.json {id: path}.

    Each icon contributes two vectors (image + filename text) sharing the path.
    Icons are fitted onto a white upscale canvas (aspect preserved), then CLIP
    embeds at 224×224.
    """
    require_clip_model()
    _require_deps()
    import faiss
    import numpy as np

    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    index_path = outdir / FAISS_INDEX
    map_path = outdir / FAISS_MAP
    json_path = outdir / FAISS_JSON
    for p in (index_path, map_path, json_path):
        if p.exists() and not force:
            raise FileExistsError(f"{p} exists (use -f/--force to overwrite)")

    canvas_size = parse_upscale(upscale)
    paths = iter_icon_files(icons_roots)
    if not paths:
        raise ValueError("no icon images found under the given roots")

    encoder = ClipEncoder()
    vectors: list = []
    id_to_path: dict[str, str] = {}
    map_lines: list[str] = []
    next_id = 0

    for path in paths:
        try:
            image = load_icon_rgb(path, canvas_size)
            # CLIP processor resizes to 224×224
            img_vec = encoder.encode_image(image)
            text = filename_to_text(path)
            txt_vec = encoder.encode_text(text)
        except Exception as e:
            if verbose >= 0:
                print(f"iconlib: skip {path}: {e}", flush=True)
            continue

        rel = str(path)
        for root in icons_roots:
            try:
                rel = str(path.resolve().relative_to(root.resolve()))
                break
            except ValueError:
                continue

        for vec in (img_vec, txt_vec):
            vid = str(next_id)
            vectors.append(np.asarray(vec, dtype=np.float32))
            id_to_path[vid] = rel
            map_lines.append(f"{vid}\t{rel}")
            next_id += 1

        if verbose > 0:
            print(f"iconlib: faiss {path} ({text})", flush=True)

    if not vectors:
        raise ValueError("no icons could be encoded")

    mat = np.vstack(vectors).astype(np.float32)
    index = faiss.IndexFlatIP(mat.shape[1])
    index.add(mat)
    faiss.write_index(index, str(index_path))
    map_path.write_text("\n".join(map_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(id_to_path, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(paths)


def find_faiss_dir(lib_path: Path, meta_path: Path | None = None) -> Path | None:
    """Locate a directory containing faiss.index + faiss.map for a library."""
    candidates: list[Path] = [lib_path, lib_path / "preview"]
    if meta_path is not None:
        # meta_path is normally a drop-in file; FAISS lives beside icons, not meta.
        if meta_path.is_dir():
            candidates.append(meta_path)
        elif meta_path.parent.is_dir():
            candidates.append(meta_path.parent)
    for d in candidates:
        if (d / FAISS_INDEX).is_file() and (d / FAISS_MAP).is_file():
            return d
    return None


def load_faiss_map(map_path: Path) -> dict[int, str]:
    """Parse faiss.map lines: id TAB path."""
    out: dict[int, str] = {}
    for raw in map_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            continue
        sid, path = line.split("\t", 1)
        out[int(sid)] = path
    return out


def path_to_icon_name(rel_path: str) -> str:
    """Derive icon search name from an indexed relative path."""
    return Path(rel_path).stem


def query_faiss_dir(
    faiss_dir: Path,
    query: str,
    *,
    encoder: ClipEncoder | None = None,
    top_k: int = 32,
) -> list[tuple[float, str]]:
    """
    Query one FAISS index with a text string.

    Returns (score, relative_path) with score in roughly 0..100 (CLIP IP × 100),
    best score kept per path.
    """
    import faiss
    import numpy as np

    index_path = faiss_dir / FAISS_INDEX
    map_path = faiss_dir / FAISS_MAP
    if not index_path.is_file() or not map_path.is_file():
        return []

    id_map = load_faiss_map(map_path)
    if not id_map:
        return []

    enc = encoder or ClipEncoder()
    vec = np.asarray(enc.encode_text(query), dtype=np.float32).reshape(1, -1)
    index = faiss.read_index(str(index_path))
    k = min(top_k, index.ntotal)
    if k <= 0:
        return []
    scores, ids = index.search(vec, k)

    best: dict[str, float] = {}
    for score, idx in zip(scores[0], ids[0], strict=False):
        if idx < 0:
            continue
        rel = id_map.get(int(idx))
        if not rel:
            continue
        s = float(score) * 100.0
        if rel not in best or s > best[rel]:
            best[rel] = s
    return sorted(((s, p) for p, s in best.items()), key=lambda x: -x[0])


def query_libraries_faiss(
    libs: list,
    query: str,
    *,
    top_k: int = 32,
    verbose: int = 0,
) -> list[tuple[float, str, str]]:
    """
    Query FAISS indexes for libraries that have one.

    Returns (score, library_name, icon_name) sorted by score descending.
    Skips libraries without an index. If CLIP is missing, raises RuntimeError.
    """
    from .paths import Library

    plain_libs = [lib for lib in libs if isinstance(lib, Library)]
    indexed: list[tuple] = []
    for lib in plain_libs:
        d = find_faiss_dir(lib.path, lib.meta_path)
        if d is not None:
            indexed.append((lib, d))
    if not indexed:
        return []

    require_clip_model()
    _require_deps()
    encoder = ClipEncoder()

    best: dict[tuple[str, str], float] = {}
    for lib, faiss_dir in indexed:
        if verbose > 0:
            print(f"iconlib: FAISS query {lib.name} ← {faiss_dir}", file=sys.stderr)
        try:
            hits = query_faiss_dir(faiss_dir, query, encoder=encoder, top_k=top_k)
        except Exception as e:
            if verbose >= 0:
                print(
                    f"iconlib: FAISS query failed for {lib.name}: {e}",
                    file=sys.stderr,
                )
            continue
        for score, rel in hits:
            name = path_to_icon_name(rel)
            key = (lib.name, name)
            if key not in best or score > best[key]:
                best[key] = score

    out = [(s, lib, name) for (lib, name), s in best.items()]
    out.sort(key=lambda x: (-x[0], x[1], x[2]))
    return out
