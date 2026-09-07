from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import create_report_run, report_pipeline
from scripts.build_method_prompt_packs import MANIFEST, build as build_prompt
from scripts.export_method_packet_schema import build_schema


ROOT = Path(__file__).resolve().parents[1]


class PersistentRunWorkflowTest(unittest.TestCase):
    def test_run_is_created_inside_repository_workspace_and_can_resume(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            fake_root = Path(temp_dir)
            (fake_root / "internal").mkdir()
            manifest = {
                "version": "2.20.0",
                "report_pipeline": {"core_version": "0.14.0"},
            }
            manifest_path = fake_root / "internal/core-manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(create_report_run, "ROOT", fake_root), patch.object(
                create_report_run, "MANIFEST", manifest_path
            ):
                state = create_report_run.create_run("resume-test")
            run_dir = Path(state["work_dir"])
            self.assertTrue((run_dir / "run-state.json").is_file())
            with patch.object(report_pipeline, "ROOT", fake_root):
                first = report_pipeline.status(run_dir)
                second = report_pipeline.status(run_dir)
            self.assertEqual(first, second)
            self.assertEqual(first["next_stage"], "core_input")

    def test_repository_under_system_tmp_is_rejected(self) -> None:
        with patch.object(create_report_run, "ROOT", Path("/tmp/rensheng-youji")):
            with self.assertRaisesRegex(ValueError, "临时目录"):
                create_report_run.create_run("should-stop")

    def test_method_prompt_uses_only_common_and_own_guide(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        prompt, receipt = build_prompt({"chart_facts": {"pillars": ["a", "b", "c", "d"]}}, "pattern_structure", manifest)
        self.assertIn("格局法｜pattern_structure", prompt)
        self.assertNotIn("调候法｜climate_adjustment", prompt)
        self.assertEqual(receipt["method_id"], "pattern_structure")
        self.assertLess(receipt["prompt_bytes"], 20_000)

    def test_exported_method_schema_matches_core_definitions(self) -> None:
        core = json.loads(
            (ROOT / "internal/rensheng-youji-mingli-core/schemas/analysis-output.schema.json").read_text(encoding="utf-8")
        )
        exported = json.loads(
            (ROOT / "internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(exported, build_schema(core))


if __name__ == "__main__":
    unittest.main()
