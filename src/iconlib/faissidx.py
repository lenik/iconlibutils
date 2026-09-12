# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build FAISS indexes from icon images + filename text via CLIP."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

IMAGE_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_SIZE = 224
JINA_CLIP_MODEL_ID = "jinaai/jina-clip-v2"
JINA_CLIP_SIZE = 512
# Index basename (no extension). Shards: faiss.1, faiss.2, …
FAISS_BASENAME = "faiss"
FAISS2_BASENAME = "faiss2"
FAISS_MAP_SUFFIX = ".map"
FAISS_JSON_SUFFIX = ".json"
FAISS_EN_JSON_SUFFIX = "-en.json"
FAISS_ZH_JSON_SUFFIX = "-zh.json"
# Legacy names still accepted when reading.
FAISS_INDEX_LEGACY = "faiss.index"
FAISS_MAP_LEGACY = "faiss.map"
FAISS_JSON_LEGACY = "faiss.json"

_FILENAME_SEP_RE = re.compile(r"[_\-./\\+|]+")


def _shard_re(prefix: str) -> re.Pattern[str]:
    """Match ``prefix`` or numbered shards ``prefix.N``."""
    return re.compile(rf"^{re.escape(prefix)}(?:\.\d+)?$")

_WEIGHT_NAMES = ("model.safetensors", "pytorch_model.bin")


def _hf_hub_cache_dir() -> Path:
    """Return the Hugging Face hub cache root (respects HF_* env vars)."""
    import os

    for key in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw).expanduser()
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        return Path(hf_home).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def _looks_like_clip_dir(path: Path) -> bool:
    if not (path / "config.json").is_file():
        return False
    return any((path / name).is_file() for name in _WEIGHT_NAMES)


def _clip_from_hf_cli() -> Path | None:
    """Locate CLIP via ``hf cache ls`` when huggingface_hub is unavailable."""
    import json as _json
    import shutil
    import subprocess

    hf = shutil.which("hf")
    if not hf:
        return None
    try:
        proc = subprocess.run(
            [
                hf,
                "cache",
                "ls",
                "--revisions",
                "--format",
                "json",
                "--filter",
                f"name={CLIP_MODEL_ID}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        entries = _json.loads(proc.stdout)
    except _json.JSONDecodeError:
        return None
    if not isinstance(entries, list):
        return None
    # Prefer newest revision; field names vary slightly across hf versions.
    def _mtime(entry: dict) -> float:
        for key in ("last_modified", "modified", "lastModified"):
            val = entry.get(key)
            if isinstance(val, (int, float)):
                return float(val)
        return 0.0

    for entry in sorted(entries, key=_mtime, reverse=True):
        if not isinstance(entry, dict):
            continue
        for key in ("snapshot_path", "snapshotPath", "path"):
            raw = entry.get(key)
            if not raw:
                continue
            path = Path(str(raw))
            if _looks_like_clip_dir(path):
                return path
    return None


def _clip_from_hf_hub() -> Path | None:
    """Locate a cached snapshot of CLIP_MODEL_ID via huggingface_hub, hf CLI, or cache layout."""
    found = _model_from_hf_hub(CLIP_MODEL_ID)
    if found is not None:
        return found
    return _clip_from_hf_cli()


def clip_download_help() -> str:
    """User-facing instructions to fetch the CLIP weights into the HF hub cache."""
    cache = _hf_hub_cache_dir()
    return (
        "CLIP model not available for FAISS indexing/search.\n"
        "\n"
        f"Expected hub id: {CLIP_MODEL_ID}\n"
        f"Hub cache: {cache}\n"
        "\n"
        "Download with the Hugging Face CLI (uses the default hub cache):\n"
        "\n"
        f"  hf download {CLIP_MODEL_ID}\n"
        "\n"
        "China mirror (optional):\n"
        "\n"
        "  export HF_ENDPOINT=https://hf-mirror.com\n"
        f"  hf download {CLIP_MODEL_ID}\n"
        "\n"
        "Or point ICONLIB_CLIP_MODEL at an existing local checkout:\n"
        "\n"
        "  export ICONLIB_CLIP_MODEL=/path/to/clip-vit-base-patch32\n"
    )


def local_clip_model() -> Path | None:
    """Return a usable local CLIP directory, or None if not downloaded."""
    import os

    env = os.environ.get("ICONLIB_CLIP_MODEL", "").strip()
    if env:
        path = Path(env).expanduser()
        if _looks_like_clip_dir(path):
            return path
        return None
    return _clip_from_hf_hub()


def require_clip_model() -> Path:
    """Require a local CLIP model; raise RuntimeError with download help if missing."""
    found = local_clip_model()
    if found is not None:
        return found
    raise RuntimeError(clip_download_help())


def resolve_clip_model() -> str:
    """
    Resolve a local CLIP directory via ICONLIB_CLIP_MODEL or the HF hub cache.

    Raises RuntimeError with download instructions when no local model exists
    (hub id alone is not enough — weights must be downloaded first).
    """
    return str(require_clip_model())


def _model_from_hf_hub(model_id: str) -> Path | None:
    """Locate a cached snapshot of *model_id* via huggingface_hub or cache layout."""
    try:
        from huggingface_hub import snapshot_download

        snap = snapshot_download(model_id, local_files_only=True)
        path = Path(snap)
        if _looks_like_clip_dir(path):
            return path
    except Exception:
        pass

    try:
        from huggingface_hub import scan_cache_dir

        cache = scan_cache_dir()
        for repo in cache.repos:
            if repo.repo_id != model_id:
                continue
            revisions = sorted(
                repo.revisions,
                key=lambda r: getattr(r, "last_modified", 0) or 0,
                reverse=True,
            )
            for rev in revisions:
                path = Path(rev.snapshot_path)
                if _looks_like_clip_dir(path):
                    return path
    except Exception:
        pass

    repo_dir = _hf_hub_cache_dir() / ("models--" + model_id.replace("/", "--"))
    snaps = repo_dir / "snapshots"
    if snaps.is_dir():
        for snap in sorted(snaps.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if snap.is_dir() and _looks_like_clip_dir(snap):
                return snap
    return None


def jina_clip_download_help() -> str:
    """User-facing instructions to fetch Jina CLIP v2 weights into the HF hub cache."""
    cache = _hf_hub_cache_dir()
    return (
        "Jina CLIP v2 model not available for FAISS2 indexing/search.\n"
        "\n"
        f"Expected hub id: {JINA_CLIP_MODEL_ID}\n"
        f"Hub cache: {cache}\n"
        "\n"
        "Download with the Hugging Face CLI (uses the default hub cache):\n"
        "\n"
        f"  hf download {JINA_CLIP_MODEL_ID}\n"
        "\n"
        "China mirror (optional):\n"
        "\n"
        "  export HF_ENDPOINT=https://hf-mirror.com\n"
        f"  hf download {JINA_CLIP_MODEL_ID}\n"
        "\n"
        "Or point ICONLIB_CLIP2_MODEL at an existing local checkout:\n"
        "\n"
        "  export ICONLIB_CLIP2_MODEL=/path/to/jina-clip-v2\n"
    )


def local_jina_clip_model() -> Path | None:
    """Return a usable local Jina CLIP directory, or None if not downloaded."""
    import os

    env = os.environ.get("ICONLIB_CLIP2_MODEL", "").strip()
    if env:
        path = Path(env).expanduser()
        if _looks_like_clip_dir(path):
            return path
        return None
    return _model_from_hf_hub(JINA_CLIP_MODEL_ID)


def require_jina_clip_model() -> Path:
    """Require a local Jina CLIP model; raise RuntimeError with download help."""
    found = local_jina_clip_model()
    if found is not None:
        return found
    raise RuntimeError(jina_clip_download_help())


def resolve_jina_clip_model() -> str:
    """Resolve local Jina CLIP v2 directory (ICONLIB_CLIP2_MODEL or HF cache)."""
    return str(require_jina_clip_model())


def parse_upscale(size: str) -> tuple[int, int]:
    """Parse SIZE as N or NxN / N×N into (width, height)."""
    raw = size.strip().lower().replace("×", "x")
    if "x" in raw:
        a, b = raw.split("x", 1)
        return int(a), int(b)
    n = int(raw)
    return n, n


_BYTE_SIZE_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([kmgt]i?b?|b)?\s*$", re.IGNORECASE
)


def parse_byte_size(size: str | int | None) -> int:
    """
    Parse a human size (``10M``, ``10MiB``, ``1024``) into bytes.

    Empty / ``0`` / ``none`` / ``off`` → ``0`` (no shard limit).
    Suffixes: K/M/G/T are binary (1024**n); KB/MB… and KiB/MiB… accepted.
    """
    if size is None:
        return 0
    if isinstance(size, int):
        return max(0, size)
    raw = str(size).strip()
    if not raw or raw.lower() in ("0", "none", "off", "unlimited", "-"):
        return 0
    m = _BYTE_SIZE_RE.match(raw)
    if not m:
        raise ValueError(f"invalid size {size!r} (expected e.g. 10M, 512K, 0)")
    amount = float(m.group(1))
    unit = (m.group(2) or "b").lower()
    if unit in ("b",):
        mult = 1
    elif unit in ("k", "kb", "ki", "kib"):
        mult = 1024
    elif unit in ("m", "mb", "mi", "mib"):
        mult = 1024**2
    elif unit in ("g", "gb", "gi", "gib"):
        mult = 1024**3
    elif unit in ("t", "tb", "ti", "tib"):
        mult = 1024**4
    else:
        raise ValueError(f"invalid size unit in {size!r}")
    return int(amount * mult)


def filename_to_text(path: Path) -> str:
    """Convert icon filename stem into a CLIP text phrase."""
    stem = path.stem
    text = _FILENAME_SEP_RE.sub(" ", stem)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or stem


def load_icon_rgb(path: Path, canvas_size: tuple[int, int]):
    """Load icon onto a white RGB canvas, preserving aspect ratio."""
    from PIL import Image

    from .svgconv import svg_to_pil

    w, h = canvas_size
    suffix = path.suffix.lower()
    if suffix == ".svg":
        img = svg_to_pil(path, width=w, height=h, background_color="white")
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
        missing.append("faiss (apt: python3-faiss)")
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("PIL (apt: python3-pil)")
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        missing.append("cairosvg (apt: python3-cairosvg)")
    try:
        import torch  # noqa: F401
    except ImportError:
        missing.append("torch (apt: python3-torch)")
    try:
        from transformers import CLIPModel, CLIPProcessor  # noqa: F401
    except ImportError:
        missing.append(
            "transformers (no Debian package; "
            "pip install --user --break-system-packages transformers)"
        )
    if missing:
        raise RuntimeError(
            "FAISS indexing requires: " + "; ".join(missing)
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


class JinaClipEncoder:
    """Lazy Jina CLIP v2 image/text encoder (1024-d, multilingual)."""

    def __init__(self, model_id: str | None = None) -> None:
        import numpy as np
        import torch
        from transformers import AutoModel

        model_id = model_id or resolve_jina_clip_model()
        self.torch = torch
        self.np = np
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self.model = AutoModel.from_pretrained(
                model_id, trust_remote_code=True
            ).to(self.device)
        except Exception as e:
            raise RuntimeError(
                f"failed to load Jina CLIP model {model_id!r}: {e}"
            ) from e
        self.model.eval()

    def _normalize(self, feats) -> "np.ndarray":
        np = self.np
        arr = np.asarray(feats, dtype=np.float32)
        if arr.ndim > 1:
            arr = arr[0]
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def encode_image(self, image) -> "np.ndarray":
        torch = self.torch
        with torch.no_grad():
            feats = self.model.encode_image([image], truncate_dim=None)
            if hasattr(feats, "detach"):
                feats = feats.detach().cpu().float().numpy()
        return self._normalize(feats)

    def encode_text(self, text: str) -> "np.ndarray":
        torch = self.torch
        with torch.no_grad():
            feats = self.model.encode_text([text], truncate_dim=None)
            if hasattr(feats, "detach"):
                feats = feats.detach().cpu().float().numpy()
        return self._normalize(feats)


def _make_encoder(kind: str | ClipEncoder | JinaClipEncoder | None, basename: str):
    """Resolve encoder kind or instance from *kind* and *basename*."""
    if isinstance(kind, (ClipEncoder, JinaClipEncoder)):
        return kind
    if kind == "openai" or (kind is None and basename == FAISS_BASENAME):
        require_clip_model()
        return ClipEncoder()
    if kind == "jina" or (kind is None and basename == FAISS2_BASENAME):
        require_jina_clip_model()
        return JinaClipEncoder()
    if kind is None:
        require_clip_model()
        return ClipEncoder()
    raise ValueError(f"unknown encoder kind {kind!r} (use 'openai' or 'jina')")


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


def _xz_compress_file(path: Path) -> Path:
    """Write ``path.xz`` beside *path* (overwrite) and return the xz path."""
    import lzma

    xz_path = Path(str(path) + ".xz")
    with path.open("rb") as src, lzma.open(
        xz_path, "wb", format=lzma.FORMAT_XZ, preset=6
    ) as dst:
        dst.write(src.read())
    return xz_path


def _write_one_faiss_shard(
    *,
    outdir: Path,
    basename: str,
    vectors: list,
    rel_paths: list[str],
    en_texts: list[str],
    force: bool,
    write_zh: bool = False,
    compress: bool = False,
) -> Path:
    """
    Write one shard: ``basename``, ``basename.map``, ``basename.json``,
    ``basename-en.json``, and optionally ``basename-zh.json``.

    *rel_paths[i]* / *en_texts[i]* belong to vector *i*. Returns the index path.
    """
    import faiss
    import numpy as np

    index_path = outdir / basename
    map_path = outdir / f"{basename}{FAISS_MAP_SUFFIX}"
    json_path = outdir / f"{basename}{FAISS_JSON_SUFFIX}"
    en_json_path = outdir / f"{basename}{FAISS_EN_JSON_SUFFIX}"
    zh_json_path = outdir / f"{basename}{FAISS_ZH_JSON_SUFFIX}"
    sidecars = [index_path, map_path, json_path, en_json_path]
    if write_zh:
        sidecars.append(zh_json_path)
    for p in sidecars:
        if p.exists() and not force:
            raise FileExistsError(f"{p} exists (use -f/--force to overwrite)")
        xz = Path(str(p) + ".xz")
        if xz.exists() and not force:
            raise FileExistsError(f"{xz} exists (use -f/--force to overwrite)")

    mat = np.vstack(vectors).astype(np.float32)
    index = faiss.IndexFlatIP(mat.shape[1])
    index.add(mat)
    faiss.write_index(index, str(index_path))

    id_to_paths: dict[str, list[str]] = {}
    id_to_en: dict[str, str] = {}
    map_lines: list[str] = []
    for i, (rel, en) in enumerate(zip(rel_paths, en_texts, strict=True)):
        vid = str(i)
        id_to_paths.setdefault(vid, []).append(rel)
        id_to_en[vid] = en
        map_lines.append(f"{vid}\t{rel}")
    map_path.write_text("\n".join(map_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(id_to_paths, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    en_json_path.write_text(
        json.dumps(id_to_en, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if write_zh:
        # Without a translator, reuse the English filename phrase for now.
        zh_json_path.write_text(
            json.dumps(id_to_en, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if compress:
        for p in sidecars:
            _xz_compress_file(p)
            p.unlink(missing_ok=True)

    return index_path


def _path_group_key(rel: str, depth: int = 1) -> str:
    parts = Path(rel).parts
    if not parts:
        return ""
    return "/".join(parts[: min(depth, len(parts))])


def vectors_per_shard(dim: int, shard_size: int) -> int:
    """
    Estimate how many float32 vectors fit in an IndexFlatIP of ~*shard_size* bytes.

    CLIP ViT-B/32 uses dim=512 → 2048 bytes/vector; FAISS header is negligible.
    *shard_size* is a rough budget for the raw ``faiss`` file (not xz).
    """
    if shard_size <= 0:
        return 0
    bytes_per_vec = max(1, int(dim) * 4)
    # Leave a little room for the IndexFlat header (~tens of bytes).
    return max(1, (shard_size - 64) // bytes_per_vec)


def _partition_by_shard_size(
    vectors: list,
    rel_paths: list[str],
    shard_size: int,
    *,
    verbose: int = 0,
) -> list[tuple[list, list[str]]]:
    """
    Split vectors into shards of roughly *shard_size* raw FAISS bytes.

    Uses fixed CLIP dim → vectors-per-shard; groups by path prefix when packing
    so related icons stay together. Final sizes only need to be approximately
    near the budget — not exact.
    """
    import numpy as np

    if shard_size <= 0 or not vectors:
        return [(vectors, rel_paths)]

    dim = int(np.asarray(vectors[0]).shape[-1])
    max_vecs = vectors_per_shard(dim, shard_size)
    if len(vectors) <= max_vecs:
        return [(vectors, rel_paths)]

    groups: dict[str, list[int]] = {}
    for i, rel in enumerate(rel_paths):
        key = _path_group_key(rel, 1) or "_"
        groups.setdefault(key, []).append(i)

    def emit_indices(idxs: list[int]) -> list[list[int]]:
        if len(idxs) <= max_vecs:
            return [idxs]
        sub: dict[str, list[int]] = {}
        for i in idxs:
            key = _path_group_key(rel_paths[i], 2) or _path_group_key(
                rel_paths[i], 1
            )
            sub.setdefault(key, []).append(i)
        if len(sub) > 1:
            out: list[list[int]] = []
            for part in sub.values():
                out.extend(emit_indices(part))
            return out
        return [
            idxs[start : start + max_vecs]
            for start in range(0, len(idxs), max_vecs)
        ]

    shards_idx: list[list[int]] = []
    pending: list[int] = []
    for key in sorted(groups):
        for piece in emit_indices(groups[key]):
            if len(piece) >= max_vecs:
                if pending:
                    shards_idx.append(pending)
                    pending = []
                shards_idx.extend(emit_indices(piece))
                continue
            if len(pending) + len(piece) <= max_vecs:
                pending.extend(piece)
            else:
                if pending:
                    shards_idx.append(pending)
                pending = list(piece)
    if pending:
        shards_idx.append(pending)

    result = [
        ([vectors[i] for i in idxs], [rel_paths[i] for i in idxs])
        for idxs in shards_idx
    ]
    if verbose >= 0:
        approx = max_vecs * dim * 4
        print(
            f"iconlib: sharding into {len(result)} parts "
            f"(~{max_vecs} vectors/shard ≈ {approx} bytes raw @ dim={dim})",
            flush=True,
        )
    return result


def _clear_faiss_outputs(outdir: Path, basename: str = FAISS_BASENAME) -> None:
    """Remove existing index shards (+ map/json/en/zh / xz / legacy) artifacts."""
    shard_re = _shard_re(basename)
    for child in list(outdir.iterdir()):
        n = child.name
        if n.endswith(".xz"):
            n = n[: -len(".xz")]
        base = n
        for suffix in (
            FAISS_MAP_SUFFIX,
            FAISS_EN_JSON_SUFFIX,
            FAISS_ZH_JSON_SUFFIX,
            FAISS_JSON_SUFFIX,
        ):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        if basename == FAISS_BASENAME and base in (
            FAISS_INDEX_LEGACY,
            FAISS_MAP_LEGACY,
            FAISS_JSON_LEGACY,
        ):
            child.unlink(missing_ok=True)
            continue
        if base == basename or shard_re.match(base):
            child.unlink(missing_ok=True)


def generate_faiss_index(
    *,
    icons_roots: list[Path],
    outdir: Path,
    upscale: str = "300x300",
    force: bool = False,
    verbose: int = 0,
    basename: str = FAISS_BASENAME,
    shard_size: int = 0,
    encoder: str | ClipEncoder | JinaClipEncoder | None = None,
    compress: bool = False,
    write_zh: bool | None = None,
) -> int:
    """
    Write ``faiss`` / ``faiss2`` (or ``.N`` shards) plus sidecar files.

    *shard_size* is an approximate max size in bytes for each raw FAISS index
    file (not xz). ``0`` means do not shard. When sharding, vector count per
    shard is derived from embedding dim × 4 bytes.

    *encoder* may be ``"openai"``, ``"jina"``, or a :class:`ClipEncoder` /
    :class:`JinaClipEncoder` instance. Defaults from *basename* when omitted.
    """
    _require_deps()
    import numpy as np

    if write_zh is None:
        write_zh = basename == FAISS2_BASENAME or encoder == "jina"

    enc = _make_encoder(encoder, basename)

    outdir = outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    canvas_size = parse_upscale(upscale)
    paths = iter_icon_files(icons_roots)
    if not paths:
        raise ValueError("no icon images found under the given roots")

    label = "Jina CLIP v2" if isinstance(enc, JinaClipEncoder) else "CLIP"
    if verbose >= 0:
        print(
            f"iconlib: FAISS indexing {len(paths)} icons "
            f"(loading {label}; this can take a while)...",
            flush=True,
        )

    vectors: list = []
    rel_paths: list[str] = []
    en_texts: list[str] = []

    for path in paths:
        try:
            image = load_icon_rgb(path, canvas_size)
            img_vec = enc.encode_image(image)
            text = filename_to_text(path)
            txt_vec = enc.encode_text(text)
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
            vectors.append(np.asarray(vec, dtype=np.float32))
            rel_paths.append(rel)
            en_texts.append(text)

        if verbose > 0:
            print(f"iconlib: {basename} {path} ({text})", flush=True)

    if not vectors:
        raise ValueError("no icons could be encoded")

    parts = _partition_by_shard_size(
        vectors, rel_paths, shard_size, verbose=verbose
    )
    # Re-partition en_texts alongside vectors/rel_paths.
    if len(parts) > 1:
        idx = 0
        reparts: list[tuple[list, list[str], list[str]]] = []
        for vecs, rels in parts:
            n = len(vecs)
            reparts.append((vecs, rels, en_texts[idx : idx + n]))
            idx += n
        parts = reparts
    else:
        parts = [(vectors, rel_paths, en_texts)]

    names = (
        [basename]
        if len(parts) == 1
        else [f"{basename}.{i}" for i in range(1, len(parts) + 1)]
    )

    if force or len(parts) > 1:
        _clear_faiss_outputs(outdir, basename)

    for name, (vecs, rels, ens) in zip(names, parts, strict=True):
        out = _write_one_faiss_shard(
            outdir=outdir,
            basename=name,
            vectors=vecs,
            rel_paths=rels,
            en_texts=ens,
            force=True,
            write_zh=write_zh,
            compress=compress,
        )
        if verbose >= 0:
            blob = out if out.is_file() else Path(str(out) + ".xz")
            size = blob.stat().st_size if blob.is_file() else 0
            print(
                f"iconlib: wrote {name} ({len(vecs)} vectors, "
                f"{size} bytes) → {blob}",
                flush=True,
            )

    return len(paths)


def _open_text_maybe_xz(path: Path) -> str:
    """Read UTF-8 text from *path* or *path.xz*."""
    import lzma

    if path.is_file():
        return path.read_text(encoding="utf-8")
    xz = Path(str(path) + ".xz")
    if xz.is_file():
        with lzma.open(xz, "rt", encoding="utf-8") as fh:
            return fh.read()
    raise FileNotFoundError(path)


def resolve_faiss_blob(base: Path) -> Path | None:
    """
    Resolve the on-disk FAISS binary for basename *base*.

    Prefers uncompressed ``base``, then ``base.xz``, then legacy ``faiss.index``.
    """
    if base.is_file():
        return base
    xz = Path(str(base) + ".xz")
    if xz.is_file():
        return xz
    # Legacy single-index name beside a directory that was named wrongly.
    if base.name == FAISS_BASENAME:
        legacy = base.with_name(FAISS_INDEX_LEGACY)
        if legacy.is_file():
            return legacy
        legacy_xz = Path(str(legacy) + ".xz")
        if legacy_xz.is_file():
            return legacy_xz
    return None


def resolve_faiss_map(base: Path) -> Path | None:
    """Resolve map sidecar for index basename *base* (``.map`` / ``.map.xz`` / legacy)."""
    mapped = Path(str(base) + FAISS_MAP_SUFFIX)
    if mapped.is_file() or Path(str(mapped) + ".xz").is_file():
        return mapped
    if base.name == FAISS_BASENAME:
        legacy = base.with_name(FAISS_MAP_LEGACY)
        if legacy.is_file() or Path(str(legacy) + ".xz").is_file():
            return legacy
        # Old layout: faiss.index + faiss.map in same dir
        sibling = base.with_name(FAISS_MAP_LEGACY)
        if sibling.is_file() or Path(str(sibling) + ".xz").is_file():
            return sibling
    # Shard: faiss.1 → faiss.1.map
    return mapped if Path(str(mapped) + ".xz").is_file() else None


def read_faiss_index(blob: Path):
    """``faiss.read_index`` supporting ``.xz`` via a temp file."""
    import lzma
    import tempfile

    import faiss

    if blob.suffix == ".xz" or str(blob).endswith(".xz"):
        with lzma.open(blob, "rb") as src:
            data = src.read()
        with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return faiss.read_index(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    return faiss.read_index(str(blob))


def discover_faiss_bases(
    directory: Path, prefix: str = FAISS_BASENAME
) -> list[Path]:
    """
    Discover FAISS basenames under *directory*.

    Returns paths like ``…/faiss`` or ``…/faiss2.1`` (no ``.xz`` / sidecars).
    Prefers numbered shards when present; otherwise a single *prefix* basename.
    """
    if not directory.is_dir():
        return []
    shard_re = _shard_re(prefix)
    shards: list[Path] = []
    single: Path | None = None
    seen: set[str] = set()
    skip_suffixes = (
        FAISS_MAP_SUFFIX,
        FAISS_JSON_SUFFIX,
        FAISS_EN_JSON_SUFFIX,
        FAISS_ZH_JSON_SUFFIX,
    )
    for child in sorted(directory.iterdir()):
        name = child.name
        if name.endswith(".xz"):
            name = name[: -len(".xz")]
        if any(name.endswith(s) for s in skip_suffixes):
            continue
        if prefix == FAISS_BASENAME and name in (
            FAISS_MAP_LEGACY,
            FAISS_JSON_LEGACY,
            FAISS_INDEX_LEGACY,
        ):
            if name == FAISS_INDEX_LEGACY and prefix not in seen:
                single = directory / prefix
                seen.add(prefix)
            continue
        if not shard_re.match(name):
            continue
        if name in seen:
            continue
        seen.add(name)
        base = directory / name
        if resolve_faiss_blob(base) is None:
            continue
        if name == prefix:
            single = base
        else:
            shards.append(base)
    if shards:
        return shards
    if single is not None and resolve_faiss_blob(single) is not None:
        return [single]
    return []


def resolve_library_faiss_bases(
    lib, prefix: str = FAISS_BASENAME
) -> list[Path]:
    """Resolve FAISS basenames for a Library (explicit index= metadata or discover)."""
    from .paths import Library

    if not isinstance(lib, Library):
        return []
    search_dirs: list[Path] = []
    if lib.meta_path is not None:
        parent = lib.meta_path.parent if lib.meta_path.is_file() else lib.meta_path
        search_dirs.append(parent)
    search_dirs.append(lib.path)

    if prefix == FAISS2_BASENAME:
        explicit = getattr(lib, "faiss2_indexes", ()) or ()
    else:
        explicit = getattr(lib, "faiss_indexes", ()) or ()
    shard_re = _shard_re(prefix)
    if explicit:
        bases: list[Path] = []
        only_dirs = True
        for rel in explicit:
            p = Path(rel).expanduser()
            # Legacy: faiss_index=/usr/share/icons-foo (directory to search).
            if p.is_absolute() and (
                p.is_dir()
                or (not resolve_faiss_blob(p) and not shard_re.match(p.name))
            ):
                found = discover_faiss_bases(p, prefix=prefix)
                if found:
                    return found
                continue
            only_dirs = False
            if not p.is_absolute():
                candidates = []
                if lib.meta_path is not None:
                    candidates.append(lib.meta_path.parent / p)
                candidates.append(lib.path / p)
                for c in candidates:
                    if resolve_faiss_blob(c) is not None:
                        bases.append(c)
                        break
                else:
                    bases.append(candidates[0])
            else:
                bases.append(p)
        if bases:
            return bases
        if only_dirs:
            pass  # fall through to discovery
        else:
            return bases

    for d in search_dirs:
        found = discover_faiss_bases(d, prefix=prefix)
        if found:
            return found
        if prefix == FAISS_BASENAME and (
            (d / FAISS_INDEX_LEGACY).is_file()
            or (d / f"{FAISS_INDEX_LEGACY}.xz").is_file()
        ):
            return [d / FAISS_BASENAME]
    return []


def find_faiss_dir(
    lib_path: Path,
    meta_path: Path | None = None,
    faiss_index: Path | str | None = None,
    faiss_indexes: tuple[str, ...] | None = None,
) -> Path | None:
    """
    Locate a directory that contains at least one FAISS index.

    Kept for compatibility; prefer :func:`resolve_library_faiss_bases`.
    """
    from .paths import Library

    indexes = faiss_indexes
    if indexes is None and isinstance(faiss_index, str) and "," in faiss_index:
        indexes = tuple(p.strip() for p in faiss_index.split(",") if p.strip())
    elif indexes is None and faiss_index is not None and not isinstance(
        faiss_index, (str, Path)
    ):
        indexes = ()
    lib = Library(
        type="auto",
        name="_",
        path=Path(lib_path),
        faiss_indexes=indexes
        or (
            (str(faiss_index),)
            if faiss_index is not None and str(faiss_index)
            else ()
        ),
        meta_path=meta_path,
    )
    bases = resolve_library_faiss_bases(lib)
    if not bases:
        return None
    return bases[0].parent


def load_faiss_map(map_path: Path) -> dict[int, list[str]]:
    """Parse faiss.map: id TAB path (same id may appear on multiple lines)."""
    out: dict[int, list[str]] = {}
    text = _open_text_maybe_xz(map_path)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            continue
        sid, path = line.split("\t", 1)
        out.setdefault(int(sid), []).append(path)
    return out


def path_to_icon_name(rel_path: str) -> str:
    """Derive icon search name from an indexed relative path."""
    return Path(rel_path).stem


def query_faiss_base(
    base: Path,
    query: str,
    *,
    encoder: ClipEncoder | JinaClipEncoder | None = None,
    top_k: int = 32,
) -> list[tuple[float, str]]:
    """
    Query one FAISS shard basename with a text string.

    Returns (score, relative_path) with score in roughly 0..100 (CLIP IP × 100),
    best score kept per path.
    """
    import numpy as np

    blob = resolve_faiss_blob(base)
    map_path = resolve_faiss_map(base)
    if blob is None or map_path is None:
        return []

    id_map = load_faiss_map(map_path)
    if not id_map:
        return []

    if encoder is None:
        prefix = base.name.split(".")[0]
        enc = _make_encoder(None, prefix)
    else:
        enc = encoder
    vec = np.asarray(enc.encode_text(query), dtype=np.float32).reshape(1, -1)
    index = read_faiss_index(blob)
    k = min(top_k, index.ntotal)
    if k <= 0:
        return []
    scores, ids = index.search(vec, k)

    best: dict[str, float] = {}
    for score, idx in zip(scores[0], ids[0], strict=False):
        if idx < 0:
            continue
        paths = id_map.get(int(idx)) or []
        s = float(score) * 100.0
        for rel in paths:
            if rel not in best or s > best[rel]:
                best[rel] = s
    return sorted(((s, p) for p, s in best.items()), key=lambda x: -x[0])


def query_faiss_dir(
    faiss_dir: Path,
    query: str,
    *,
    encoder: ClipEncoder | JinaClipEncoder | None = None,
    top_k: int = 32,
    prefix: str = FAISS_BASENAME,
) -> list[tuple[float, str]]:
    """Query all FAISS shards discovered under *faiss_dir*."""
    bases = discover_faiss_bases(faiss_dir, prefix=prefix)
    if not bases and resolve_faiss_blob(faiss_dir / prefix):
        bases = [faiss_dir / prefix]
    best: dict[str, float] = {}
    for base in bases:
        for score, rel in query_faiss_base(
            base, query, encoder=encoder, top_k=top_k
        ):
            if rel not in best or score > best[rel]:
                best[rel] = score
    return sorted(((s, p) for p, s in best.items()), key=lambda x: -x[0])


def query_libraries_faiss(
    libs: list,
    query: str,
    *,
    top_k: int = 32,
    verbose: int = 0,
    prefix: str = FAISS_BASENAME,
    encoder: ClipEncoder | JinaClipEncoder | None = None,
) -> list[tuple[float, str, str]]:
    """
    Query FAISS indexes for libraries that have one.

    Returns (score, library_name, icon_name) sorted by score descending.
    Skips libraries without an index. Raises RuntimeError if the model is missing.
    """
    from .paths import Library

    plain_libs = [lib for lib in libs if isinstance(lib, Library)]
    indexed: list[tuple] = []
    for lib in plain_libs:
        bases = resolve_library_faiss_bases(lib, prefix=prefix)
        if bases:
            indexed.append((lib, bases))
    if not indexed:
        return []

    _require_deps()
    enc = encoder or _make_encoder(None, prefix)

    best: dict[tuple[str, str], float] = {}
    for lib, bases in indexed:
        if verbose > 0:
            labels = ", ".join(b.name for b in bases)
            print(f"iconlib: FAISS query {lib.name} ← {labels}", file=sys.stderr)
        for base in bases:
            try:
                hits = query_faiss_base(
                    base, query, encoder=enc, top_k=top_k
                )
            except Exception as e:
                if verbose >= 0:
                    print(
                        f"iconlib: FAISS query failed for {lib.name}/{base.name}: {e}",
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
