from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from iconlib.autoindex import (
    compile_pattern,
    filter_groups,
    index_libraries,
    normalize_size,
    parse_rel_path,
    parse_size_args,
    prefer_asset,
    search_groups,
)
from iconlib.paths import Library, load_libraries, resolve_library_names
from iconlib.rc import find_iconlibrc, load_rc, parse_rc_text
from iconlib.cmd.pull import expand_dest, parse_schema
from iconlib.semantic import (
    expand_query_terms,
    inflection_forms,
    is_plain_query,
    score_icon_name,
)


class PathRegistryTests(unittest.TestCase):
    def test_parse_and_merge_legacy_path_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            etc = Path(td) / "etc-path"
            user = Path(td) / "user-path"
            etc.write_text(
                "# comment\n\nauto tabler-icons /usr/share/tabler-icons\n"
                "auto old /tmp/old\n",
                encoding="utf-8",
            )
            user.write_text("auto old /tmp/new\nauto mdi /usr/share/mdi\n", encoding="utf-8")
            libs = load_libraries(library_dirs=[], path_files=[etc, user])
            self.assertEqual(libs["old"].path, Path("/tmp/new"))
            self.assertIn("tabler-icons", libs)
            self.assertIn("mdi", libs)

    def test_library_file_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "library"
            root.mkdir(parents=True)
            (root / "lucide").write_text(
                "name=lucide\n"
                "type=auto\n"
                "path=/usr/share/icons-lucide\n"
                "title=Lucide\n"
                "license=ISC\n"
                "homepage=https://lucide.dev/\n",
                encoding="utf-8",
            )
            (root / "feather").write_text(
                "path=/opt/feather\ntitle=Feather\n",
                encoding="utf-8",
            )
            libs = load_libraries(library_dirs=[root], path_files=[])
            self.assertEqual(set(libs), {"lucide", "feather"})
            self.assertEqual(libs["lucide"].path, Path("/usr/share/icons-lucide"))
            self.assertEqual(libs["lucide"].title, "Lucide")
            self.assertEqual(libs["lucide"].license, "ISC")
            self.assertEqual(libs["lucide"].meta_path, root / "lucide")
            self.assertEqual(libs["feather"].name, "feather")
            self.assertEqual(libs["feather"].path, Path("/opt/feather"))

    def test_library_dir_ignored(self) -> None:
        """Directory form …/library/<name>/ is not discovered."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "library"
            lucide = root / "lucide"
            lucide.mkdir(parents=True)
            (lucide / "library.conf").write_text(
                "name=lucide\npath=/usr/share/icons-lucide\n",
                encoding="utf-8",
            )
            libs = load_libraries(library_dirs=[root], path_files=[])
            self.assertEqual(libs, {})

    def test_prefix_resolve(self) -> None:
        reg = {
            "tabler-icons": Library("auto", "tabler-icons", Path("/t")),
            "tabler-extra": Library("auto", "tabler-extra", Path("/e")),
            "streamline-vectors": Library("auto", "streamline-vectors", Path("/s")),
        }
        got = resolve_library_names(reg, ["stream"])
        self.assertEqual([g.name for g in got], ["streamline-vectors"])
        with self.assertRaises(KeyError):
            resolve_library_names(reg, ["tabler"])
        got2 = resolve_library_names(reg, ["tabler-i"])
        self.assertEqual(got2[0].name, "tabler-icons")


class LibrariesCommandTests(unittest.TestCase):
    def test_libraries_lists_names(self) -> None:
        import os
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "library"
            root.mkdir(parents=True)
            (root / "lucide").write_text(
                "name=lucide\npath=/tmp/lucide-icons\ntitle=Lucide\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["ICONLIBUTILS_LIBRARY_DIRS"] = str(root)
            env["ICONLIBUTILS_PATH_FILES"] = ""
            env["PYTHONPATH"] = str(
                Path(__file__).resolve().parents[1] / "src"
            )
            proc = subprocess.run(
                [sys.executable, "-m", "iconlib", "libraries", "-1"],
                cwd=str(Path(__file__).resolve().parents[1] / "src"),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "lucide")


class RcTests(unittest.TestCase):
    def test_parse_rc(self) -> None:
        opts = parse_rc_text("-l tabler\n# x\n-d assets\n-s l/f/n\n-m tabler=ti\n")
        self.assertEqual(opts.libraries, ["tabler"])
        self.assertEqual(opts.local_dir, "assets")
        self.assertEqual(opts.schema, "l/f/n")
        self.assertEqual(opts.maps["tabler"], "ti")

    def test_find_rc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sub = root / "a" / "b"
            sub.mkdir(parents=True)
            (root / ".iconlibrc").write_text("-d icons\n", encoding="utf-8")
            found = find_iconlibrc(sub)
            self.assertEqual(found, root / ".iconlibrc")
            loaded = load_rc(sub)
            self.assertEqual(loaded.project_dir, root)
            self.assertEqual(loaded.local_dir, "icons")


class AutoIndexTests(unittest.TestCase):
    def test_parse_tabler_style(self) -> None:
        name, size, variant, fmt = parse_rel_path(Path("svg/outline/home.svg"))
        self.assertEqual((name, size, variant, fmt), ("home", None, "outline", "svg"))
        name, size, variant, fmt = parse_rel_path(Path("png/filled/16x16/home.png"))
        self.assertEqual(name, "home")
        self.assertEqual(size, "16x16")
        self.assertEqual(variant, "filled")
        self.assertEqual(fmt, "png")

    def test_parse_phosphor_suffix(self) -> None:
        name, size, variant, fmt = parse_rel_path(Path("SVGs/bold/pause-circle-bold.svg"))
        self.assertEqual(name, "pause-circle")
        self.assertEqual(variant, "bold")
        self.assertEqual(fmt, "svg")

    def test_index_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "tabler-icons"
            (root / "svg" / "outline").mkdir(parents=True)
            (root / "png" / "outline" / "16x16").mkdir(parents=True)
            (root / "svg" / "outline" / "home.svg").write_text("<svg/>", encoding="utf-8")
            (root / "svg" / "outline" / "home-2.svg").write_text("<svg/>", encoding="utf-8")
            (root / "png" / "outline" / "16x16" / "home.png").write_bytes(b"png")
            lib = Library("auto", "tabler-icons", root)
            groups = index_libraries([lib])
            self.assertIn("home", groups)
            self.assertEqual(set(groups["home"].formats()), {"svg", "png"})
            matched = filter_groups(groups, "home*")
            self.assertEqual([g.name for g in matched], ["home", "home-2"])
            matched = filter_groups(groups, "/^home$")
            self.assertEqual([g.name for g in matched], ["home"])
            pref = prefer_asset(groups["home"].assets)
            assert pref is not None
            self.assertEqual(pref.format, "svg")

    def test_pattern_exact_glob(self) -> None:
        self.assertTrue(compile_pattern("ab")("ab"))
        self.assertFalse(compile_pattern("ab")("abc"))
        self.assertTrue(compile_pattern("a*")("abc"))
        self.assertTrue(compile_pattern("/^x\\d+$")("x12"))


class SchemaTests(unittest.TestCase):
    def test_parse_schema(self) -> None:
        self.assertEqual(parse_schema("l/f/n"), ["lib", "fmt", "name"])
        self.assertEqual(parse_schema("s/l/f/n"), ["size", "lib", "fmt", "name"])
        self.assertEqual(parse_schema("n"), ["name"])
        self.assertEqual(
            parse_schema("v/m/e"), ["variant", "stem", "extension"]
        )

    def test_expand_with_alias(self) -> None:
        from iconlib.autoindex import IconAsset

        asset = IconAsset(
            library="tabler-icons",
            name="foo",
            orig="png/outline/64x64/foo.png",
            path=Path("/x/foo.png"),
            format="png",
            size="64x64",
            variant="outline",
        )
        _, aliases = parse_size_args(["medium=64"])
        dest = expand_dest(asset, "s/l/f/n", size_aliases=aliases)
        self.assertEqual(dest, Path("medium/tabler-icons/png/foo.png"))
        dest2 = expand_dest(asset, "n")
        self.assertEqual(dest2, Path("foo.png"))
        dest3 = expand_dest(asset, "l/f/n", maps={"tabler-icons": "ti"})
        self.assertEqual(dest3, Path("ti/png/foo.png"))
        dest4 = expand_dest(asset, "l/v/n")
        self.assertEqual(dest4, Path("tabler-icons/outline/foo.png"))
        dest5 = expand_dest(asset, "v/m/e")
        self.assertEqual(dest5, Path("outline/foo/png"))
        dest6 = expand_dest(asset, "m")
        self.assertEqual(dest6, Path("foo"))

    def test_normalize_size(self) -> None:
        self.assertEqual(normalize_size("16"), "16x16")
        self.assertEqual(normalize_size("32x24"), "32x24")


class PullIntegrationTests(unittest.TestCase):
    def test_pull_via_main(self) -> None:
        from iconlib.cmd import main

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            libroot = td_path / "lib" / "demo"
            (libroot / "svg").mkdir(parents=True)
            (libroot / "svg" / "star.svg").write_text("<svg/>", encoding="utf-8")
            pathfile = td_path / "path"
            pathfile.write_text(f"auto demo {libroot}\n", encoding="utf-8")
            project = td_path / "proj"
            project.mkdir()
            (project / ".iconlibrc").write_text("-d assets\n-s l/f/n\n", encoding="utf-8")

            env = os.environ.copy()
            env["ICONLIBUTILS_PATH_FILES"] = str(pathfile)
            old = dict(os.environ)
            os.environ.update(env)
            try:
                cwd = Path.cwd()
                os.chdir(project)
                rc = main(
                    [
                        "iconlib",
                        "-l",
                        "demo",
                        "pull",
                        "star",
                    ]
                )
                self.assertEqual(rc, 0)
                dest = project / "assets" / "demo" / "svg" / "star.svg"
                self.assertTrue(dest.is_file())
            finally:
                os.chdir(cwd)
                os.environ.clear()
                os.environ.update(old)


class LocalCommandsTests(unittest.TestCase):
    def _project(self, td: Path) -> Path:
        project = td / "proj"
        icons = project / "icons"
        (icons / "svg").mkdir(parents=True)
        (icons / "svg" / "star.svg").write_text("<svg id='a'/>", encoding="utf-8")
        (icons / "png").mkdir(parents=True)
        (icons / "png" / "star.png").write_bytes(b"\x89PNG\r\n")
        (project / ".iconlibrc").write_text("-d icons\n", encoding="utf-8")
        return project

    def test_delete_rename_copy_ln(self) -> None:
        from iconlib.cmd import main

        with tempfile.TemporaryDirectory() as td:
            project = self._project(Path(td))
            cwd = Path.cwd()
            os.chdir(project)
            try:
                self.assertEqual(main(["iconlib", "copy", "star", "moon"]), 0)
                self.assertTrue((project / "icons" / "svg" / "moon.svg").is_file())
                self.assertTrue((project / "icons" / "png" / "moon.png").is_file())

                self.assertEqual(main(["iconlib", "ln", "-s", "moon", "luna"]), 0)
                luna = project / "icons" / "svg" / "luna.svg"
                self.assertTrue(luna.is_symlink())

                self.assertEqual(main(["iconlib", "rename", "moon", "comet"]), 0)
                self.assertFalse((project / "icons" / "svg" / "moon.svg").exists())
                self.assertTrue((project / "icons" / "svg" / "comet.svg").is_file())

                self.assertEqual(main(["iconlib", "delete", "star"]), 0)
                self.assertFalse((project / "icons" / "svg" / "star.svg").exists())
                self.assertFalse((project / "icons" / "png" / "star.png").exists())
            finally:
                os.chdir(cwd)

    def test_make_png_size(self) -> None:
        from iconlib.cmd import main

        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "proj"
            icons = project / "icons"
            icons.mkdir(parents=True)
            # Minimal valid SVG for cairosvg
            (icons / "dot.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                '<rect width="10" height="10" fill="black"/></svg>',
                encoding="utf-8",
            )
            (project / ".iconlibrc").write_text("-d icons\n", encoding="utf-8")
            cwd = Path.cwd()
            os.chdir(project)
            try:
                rc = main(["iconlib", "make", "-F", "png", "-s", "16", "dot"])
                self.assertEqual(rc, 0)
                out = project / "icons" / "16x16" / "dot.png"
                self.assertTrue(out.is_file())
                self.assertGreater(out.stat().st_size, 0)
            finally:
                os.chdir(cwd)


class SemanticTests(unittest.TestCase):
    def test_plain_query_detection(self) -> None:
        self.assertTrue(is_plain_query("cat"))
        self.assertFalse(is_plain_query(""))
        self.assertFalse(is_plain_query("cat*"))
        self.assertFalse(is_plain_query("/cat"))

    def test_inflection(self) -> None:
        forms = inflection_forms("cats")
        self.assertIn("cat", forms)
        self.assertIn("cats", forms)

    def test_score_exact_beats_related(self) -> None:
        terms = expand_query_terms("cat")
        exact = score_icon_name("cat", "cat", terms)
        other = score_icon_name("dog", "cat", terms)
        self.assertGreaterEqual(exact, 100.0)
        self.assertLess(other, exact)

    def test_search_groups_ranked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "demo"
            (root / "svg").mkdir(parents=True)
            for name in ("cat", "cats", "dog", "kitty", "home", "chess-queen"):
                (root / "svg" / f"{name}.svg").write_text("<svg/>", encoding="utf-8")
            groups = index_libraries([Library("auto", "demo", root)])
            ranked = search_groups(groups, "cat", {"demo"})
            names = [g.name for _, g in ranked]
            self.assertIn("cat", names)
            self.assertIn("cats", names)
            self.assertEqual(names[0], "cat")
            scores = {g.name: s for s, g in ranked}
            self.assertGreater(scores["cat"], scores.get("dog", 0))
            self.assertNotIn("chess-queen", names)
            from iconlib.site import get_wordnet_dir

            if not (get_wordnet_dir() / "index.noun").is_file():
                self.skipTest("wordnet-base not available")
            self.assertIn("kitty", names)
            self.assertGreater(scores["kitty"], 45.0)


class FaissHelperTests(unittest.TestCase):
    def test_parse_upscale_and_filename(self) -> None:
        from iconlib.faissidx import filename_to_text, parse_upscale

        self.assertEqual(parse_upscale("300"), (300, 300))
        self.assertEqual(parse_upscale("300x200"), (300, 200))
        self.assertEqual(filename_to_text(Path("foo_bar-baz.svg")), "foo bar baz")
        self.assertEqual(
            filename_to_text(Path("chess-queen_outline.svg")), "chess queen outline"
        )
        self.assertEqual(filename_to_text(Path("a/b/foo_bar-baz.png")), "foo bar baz")

    def test_parse_byte_size_and_vectors_per_shard(self) -> None:
        from iconlib.faissidx import parse_byte_size, vectors_per_shard

        self.assertEqual(parse_byte_size(None), 0)
        self.assertEqual(parse_byte_size("0"), 0)
        self.assertEqual(parse_byte_size("10M"), 10 * 1024 * 1024)
        self.assertEqual(parse_byte_size("10MiB"), 10 * 1024 * 1024)
        # dim=512 → 2048 bytes/vector; 10MiB ≈ 5119 vectors
        self.assertEqual(vectors_per_shard(512, 10 * 1024 * 1024), 5119)
        # dim=1024 → 4096 bytes/vector; 10MiB ≈ 2559 vectors
        self.assertEqual(vectors_per_shard(1024, 10 * 1024 * 1024), 2559)

    def test_shard_regex_and_discover(self) -> None:
        import tempfile

        from iconlib.faissidx import (
            FAISS2_BASENAME,
            FAISS_BASENAME,
            _shard_re,
            discover_faiss_bases,
        )

        self.assertTrue(_shard_re(FAISS_BASENAME).match("faiss"))
        self.assertTrue(_shard_re(FAISS_BASENAME).match("faiss.3"))
        self.assertFalse(_shard_re(FAISS_BASENAME).match("faiss2"))
        self.assertTrue(_shard_re(FAISS2_BASENAME).match("faiss2"))
        self.assertTrue(_shard_re(FAISS2_BASENAME).match("faiss2.1"))
        self.assertFalse(_shard_re(FAISS2_BASENAME).match("faiss"))

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "faiss").write_bytes(b"fake")
            (root / "faiss2").write_bytes(b"fake")
            (root / "faiss2.1").write_bytes(b"fake")
            (root / "faiss.map").write_text("0\ticon.svg\n", encoding="utf-8")
            (root / "faiss-en.json").write_text('{"0": "icon"}\n', encoding="utf-8")
            self.assertEqual(
                [p.name for p in discover_faiss_bases(root, prefix=FAISS_BASENAME)],
                ["faiss"],
            )
            self.assertEqual(
                sorted(p.name for p in discover_faiss_bases(root, prefix=FAISS2_BASENAME)),
                ["faiss2.1"],
            )

    def test_library_faiss2_indexes(self) -> None:
        from iconlib.paths import library_from_data
        from iconlib.faissidx import resolve_library_faiss_bases, FAISS2_BASENAME

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "faiss2").write_bytes(b"fake")
            lib = library_from_data(
                {"name": "demo", "path": str(root), "faiss2_index": "faiss2"},
                default_name="demo",
            )
            bases = resolve_library_faiss_bases(lib, prefix=FAISS2_BASENAME)
            self.assertEqual(len(bases), 1)
            self.assertEqual(bases[0].name, "faiss2")


if __name__ == "__main__":
    unittest.main()
