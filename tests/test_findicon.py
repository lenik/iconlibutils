from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from iconlib.ilcommon import copy_stream
import io

REPO = Path(__file__).resolve().parents[1]
SRC_FINDICON = REPO / "findicon.sh"


class FindiconTests(unittest.TestCase):
    def test_copy_stream_roundtrip(self) -> None:
        src = io.BytesIO(b"alpha\nbeta\n")
        dst = io.BytesIO()
        copy_stream(src, dst)
        self.assertEqual(dst.getvalue(), b"alpha\nbeta\n")

    def test_findicon_shell_delegates_to_search(self) -> None:
        self.assertTrue(SRC_FINDICON.is_file(), f"missing {SRC_FINDICON}")

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            script = td_path / "findicon"
            shutil.copy2(SRC_FINDICON, script)
            script.chmod(0o755)

            stub = td_path / "iconlib"
            log = td_path / "argv.log"
            stub.write_text(
                "#!/bin/bash\n"
                f'printf "%s\\n" "$@" > "{log}"\n'
                "exit 0\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)

            subprocess.run([str(script), "cat"], check=True, cwd=td_path)
            self.assertEqual(log.read_text(encoding="utf-8").strip(), "search\ncat")

            subprocess.run([str(script), "--version"], check=True, cwd=td_path)
            self.assertEqual(log.read_text(encoding="utf-8").strip(), "--version")


if __name__ == "__main__":
    unittest.main()
