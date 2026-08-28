from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import (  # noqa: E402
    get_recent_errors_v1,
    search_logs_v1,
    search_logs_v2,
    server_metadata_json,
)


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "app.log").write_text(
            "\n".join(
                [
                    "2026-08-28 09:00:00 INFO started",
                    "2026-08-28 09:01:00 ERROR first failure",
                    "2026-08-28 09:02:00 WARNING slow request",
                    "2026-08-28 09:03:00 ERROR second failure",
                    "free-form error line",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_v1_is_case_insensitive_by_default(self) -> None:
        result = search_logs_v1("app.log", "error", root=self.root)
        self.assertEqual(len(result), 3)
        self.assertIn("first failure", result[0])

    def test_recent_errors_are_newest_first(self) -> None:
        result = get_recent_errors_v1("app.log", limit=2, root=self.root)
        self.assertEqual(len(result), 2)
        self.assertIn("second failure", result[0])
        self.assertIn("first failure", result[1])

    def test_search_v2_returns_structured_metadata(self) -> None:
        result = search_logs_v2(
            "app.log", "ERROR", limit=1, case_sensitive=True, root=self.root
        )
        self.assertEqual(result["api_version"], "2.0")
        self.assertEqual(result["matched"], 2)
        self.assertEqual(result["returned"], 1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["entries"][0]["level"], "ERROR")

    def test_path_traversal_is_rejected(self) -> None:
        outside = self.root.parent / "outside.log"
        outside.write_text("ERROR outside", encoding="utf-8")
        with self.assertRaises(ValueError):
            search_logs_v1("../outside.log", "ERROR", root=self.root)
        outside.unlink(missing_ok=True)

    def test_server_metadata_describes_versioned_tools(self) -> None:
        metadata = json.loads(server_metadata_json())
        self.assertEqual(metadata["version"], "2.0.0")
        self.assertIn("search_logs", metadata["tools"])
        self.assertIn("search_logs_v2", metadata["tools"])


if __name__ == "__main__":
    unittest.main()
