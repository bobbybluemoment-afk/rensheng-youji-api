from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_runtime_entry import audit


class RuntimeAuditTest(unittest.TestCase):
    def _root(self, instruction: str) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "scripts").mkdir()
        (root / "skills").mkdir()
        (root / "internal").mkdir()
        for name in ("setup_env.py", "run_in_env.py", "check_env.py"):
            (root / "scripts" / name).touch()
        (root / "README.md").write_text(instruction, encoding="utf-8")
        (root / "SKILL.md").write_text("", encoding="utf-8")
        return temp, root

    def test_allows_bootstrap_and_launcher(self) -> None:
        temp, root = self._root(
            "python scripts/setup_env.py\n"
            "python scripts/run_in_env.py scripts/check_env.py\n"
        )
        try:
            self.assertEqual(audit(root), [])
        finally:
            temp.cleanup()

    def test_rejects_direct_business_script(self) -> None:
        temp, root = self._root("python scripts/check_env.py\n")
        try:
            errors = audit(root)
        finally:
            temp.cleanup()
        self.assertTrue(any("绕过仓库运行入口" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
