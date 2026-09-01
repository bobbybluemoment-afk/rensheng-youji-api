from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_in_env


class RuntimeEntryTest(unittest.TestCase):
    def test_runtime_path_is_cross_platform(self) -> None:
        root = Path("/repo")
        self.assertEqual(run_in_env.runtime_python(root, "posix"), root / "venv/bin/python")
        self.assertEqual(run_in_env.runtime_python(root, "nt"), root / "venv/Scripts/python.exe")

    def test_missing_runtime_stops_with_setup_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "venv/bin/python"
            stderr = io.StringIO()
            with patch.object(run_in_env, "runtime_python", return_value=missing):
                with contextlib.redirect_stderr(stderr):
                    status = run_in_env.main(["scripts/check_env.py"])
        self.assertEqual(status, 3)
        self.assertIn("scripts/setup_env.py", stderr.getvalue())

    def test_launcher_uses_repository_interpreter_and_propagates_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            python = Path(temp_dir) / "python"
            python.touch()
            with patch.object(run_in_env, "runtime_python", return_value=python):
                with patch.object(run_in_env.subprocess, "run") as mocked:
                    mocked.return_value.returncode = 7
                    status = run_in_env.main(["scripts/check_env.py", "--flag"])
        self.assertEqual(status, 7)
        mocked.assert_called_once_with(
            [str(python), "scripts/check_env.py", "--flag"],
            cwd=run_in_env.ROOT,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
