from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_documented_cli_contract import audit, documented_commands, required_options


ROOT = Path(__file__).resolve().parents[1]


class DocumentedCliContractTest(unittest.TestCase):
    def test_all_maintained_commands_supply_required_options(self) -> None:
        self.assertEqual(audit(ROOT), [])

    def test_required_argparse_option_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "sample.py"
            script.write_text(
                "import argparse\np=argparse.ArgumentParser()\np.add_argument('--input', required=True)\np.add_argument('--optional')\n",
                encoding="utf-8",
            )
            self.assertEqual(required_options(script), {"--input"})

    def test_multiline_run_in_env_command_is_parsed(self) -> None:
        commands = documented_commands(
            "```bash\npython scripts/run_in_env.py scripts/example.py \\\n\n  --input a.json \\\n\n  --output b.json\n```\n"
        )
        self.assertEqual(commands[0][2], "scripts/example.py")
        self.assertIn("--input", commands[0])
        self.assertIn("--output", commands[0])


if __name__ == "__main__":
    unittest.main()
