from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_export"


class RecoveryCliTest(unittest.TestCase):
    def test_builds_private_offline_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "recovery"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "claude_data_recovery",
                    str(FIXTURE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn('"conversation_count": 1', result.stdout)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "normalized_data.json").is_file())
            self.assertTrue((output / "memory_import.md").is_file())

            markdown_files = list((output / "markdown").glob("*.md"))
            self.assertEqual(len(markdown_files), 1)
            self.assertIn("private offline archive", markdown_files[0].read_text(encoding="utf-8"))

            normalized = json.loads((output / "normalized_data.json").read_text(encoding="utf-8"))
            self.assertEqual(normalized["stats"]["conversation_count"], 1)
            self.assertEqual(normalized["stats"]["total_message_count"], 2)

            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Claude Data Recovery", html)
            self.assertIn("Plan an offline archive", html)
            self.assertNotIn("https://cdn.", html)


if __name__ == "__main__":
    unittest.main()
