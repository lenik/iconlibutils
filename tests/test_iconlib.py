from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from autoindex import (
    compile_pattern,
    filter_groups,
    index_libraries,
    normalize_size,
    parse_rel_path,
    parse_size_args,
    prefer_asset,
    search_groups,
)
from paths import Library, load_libraries, resolve_library_names
from rc import find_iconlibrc, load_rc, parse_rc_text
from schema import expand_dest, parse_schema
from semantic import (
    expand_query_terms,
    inflection_forms,
    is_plain_query,
    score_icon_name,
)


class PathRegistryTests(unittest.TestCase):
    def test_parse_and_merge(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            etc = Path(td) / "etc-path"
            user = Path(td) / "user-path"
            etc.write_text(
                "# comment\n\nauto tabler-icons /usr/share/tabler-icons\n"
                "auto old /tmp/old\n",
                encoding="utf-8",
            )
            user.write_text("auto old /tmp/new\nauto mdi /usr/share/mdi\n", encoding="utf-8")
            libs = load_libraries([etc, user])
            self.assertEqual(libs["old"].path, Path("/tmp/new"))
            self.assertIn("tabler-icons", libs)
            self.assertIn("mdi", libs)

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
        from autoindex import IconAsset

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
        from iconlib import main

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
            try:
                import pattern.en  # noqa: F401
            except ImportError:
                self.skipTest("python3-pattern not available")
            self.assertIn("kitty", names)
            self.assertGreater(scores["kitty"], 45.0)


if __name__ == "__main__":
    unittest.main()
