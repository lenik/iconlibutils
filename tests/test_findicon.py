from __future__ import annotations

import unittest

from iconlib.ilcommon import copy_stream
import io


class FindiconTests(unittest.TestCase):
    def test_copy_stream_roundtrip(self) -> None:
        src = io.BytesIO(b"alpha\nbeta\n")
        dst = io.BytesIO()
        copy_stream(src, dst)
        self.assertEqual(dst.getvalue(), b"alpha\nbeta\n")

    def test_findicon_delegates_to_search(self) -> None:
        import sys
        from unittest import mock

        from findicon import main as findicon_main

        with mock.patch("findicon.iconlib_main", return_value=0) as m:
            rc = findicon_main(["findicon", "cat"])
            self.assertEqual(rc, 0)
            m.assert_called_once_with(["iconlib", "search", "cat"])

        with mock.patch("findicon.iconlib_main", return_value=0) as m:
            rc = findicon_main(["findicon", "--version"])
            self.assertEqual(rc, 0)
            m.assert_called_once_with(["iconlib", "--version"])


if __name__ == "__main__":
    unittest.main()
