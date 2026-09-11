# Copyright (C) 2026 Lenik <iconlibutils@bodz.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Build/search FAISS index against the bundled bytesize-icons fixture."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

BYTESIZE_ROOT = Path(__file__).resolve().parent / "bytesize-icons"
BYTESIZE_ICONS = BYTESIZE_ROOT / "dist" / "icons"


def _clip_ready() -> bool:
    from iconlib.faissidx import local_clip_model

    return local_clip_model() is not None


def _faiss_ready() -> bool:
    try:
        import faiss  # noqa: F401
        import torch  # noqa: F401
        from transformers import CLIPModel  # noqa: F401
    except ImportError:
        return False
    return _clip_ready()


@unittest.skipUnless(BYTESIZE_ICONS.is_dir(), "bytesize-icons fixture missing")
class BytesizeFaissTests(unittest.TestCase):
    @unittest.skipUnless(_faiss_ready(), "CLIP/FAISS deps or local model missing")
    def test_index_and_search_camera(self) -> None:
        from iconlib.cli import main

        self.assertTrue((BYTESIZE_ICONS / "camera.svg").is_file())
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Copy a small subset so the test stays relatively fast.
            icons = td_path / "icons"
            icons.mkdir()
            for name in (
                "camera.svg",
                "home.svg",
                "search.svg",
                "mail.svg",
                "heart.svg",
                "trash.svg",
                "user.svg",
                "settings.svg",
                "clock.svg",
                "folder.svg",
            ):
                src = BYTESIZE_ICONS / name
                if src.is_file():
                    shutil.copy2(src, icons / name)

            outdir = td_path / "index"
            pathfile = td_path / "path"
            # Library root is outdir so faiss.index is discoverable beside icons
            # via find_faiss_dir(lib.path). Put icons under outdir/icons and
            # write FAISS into outdir.
            lib_root = outdir
            lib_icons = lib_root / "icons"
            lib_icons.mkdir(parents=True)
            for p in icons.iterdir():
                shutil.copy2(p, lib_icons / p.name)

            pathfile.write_text(f"auto bytesize {lib_root}\n", encoding="utf-8")

            env = os.environ.copy()
            env["ICONLIBUTILS_PATH_FILES"] = str(pathfile)
            env["ICONLIBUTILS_LIBRARY_DIRS"] = ""
            old = dict(os.environ)
            os.environ.update(env)
            try:
                rc = main(
                    [
                        "iconlib",
                        "-l",
                        "bytesize",
                        "index",
                        "-F",
                        "-f",
                        "-o",
                        str(outdir),
                        "--icons-root",
                        str(lib_icons),
                    ]
                )
                self.assertEqual(rc, 0)
                self.assertTrue((outdir / "faiss.index").is_file())
                self.assertTrue((outdir / "faiss.map").is_file())

                import io
                from contextlib import redirect_stdout

                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = main(
                        [
                            "iconlib",
                            "-l",
                            "bytesize",
                            "search",
                            "--long",
                            "camera",
                        ]
                    )
                self.assertEqual(rc, 0)
                out = buf.getvalue()
                self.assertIn("camera", out)
                # Best hit should be camera (exact name and/or FAISS).
                first = out.splitlines()[0]
                self.assertIn("camera", first)
            finally:
                os.environ.clear()
                os.environ.update(old)

    def test_index_faiss_requires_model_message(self) -> None:
        from iconlib.faissidx import clip_download_help, local_clip_model, require_clip_model

        help_text = clip_download_help()
        self.assertIn("hfd", help_text)
        self.assertIn("openai/clip-vit-base-patch32", help_text)
        self.assertIn("HF_ENDPOINT", help_text)

        if local_clip_model() is None:
            with self.assertRaises(RuntimeError) as ctx:
                require_clip_model()
            self.assertIn("hfd", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
