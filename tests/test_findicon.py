from __future__ import annotations

import io
import unittest

from ilcommon import copy_stream


class FindiconTests(unittest.TestCase):
    def test_copy_stream_roundtrip(self) -> None:
        src = io.BytesIO(b"alpha\nbeta\n")
        dst = io.BytesIO()
        copy_stream(src, dst)
        self.assertEqual(dst.getvalue(), b"alpha\nbeta\n")


if __name__ == "__main__":
    unittest.main()
