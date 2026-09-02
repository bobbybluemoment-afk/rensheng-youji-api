from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import create_report_run, initialize_method_packets, report_pipeline
from scripts.export_method_packet_schema import build_schema


ROOT = Path(__file__).resolve().parents[1]


class PersistentRunWorkflowTest(unittest.TestCase):
    def test_run_is_created_inside_repository_workspace_and_can_resume(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            fake_root = Path(temp_dir)
            (fake_root / "internal").mkdir()
            manifest = {
                "version": "2.19.2",
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

    def test_nine_method_drafts_share_one_input_hash(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            fake_root = Path(temp_dir)
            input_path = fake_root / "method-input.json"
            input_path.write_text(json.dumps({"chart": {"pillars": ["a", "b", "c", "d"]}}), encoding="utf-8")
            output_dir = fake_root / "work/runs/test/method-packet-drafts"
            output_dir.mkdir(parents=True)
            with patch.object(initialize_method_packets, "ROOT", fake_root):
                with patch("sys.argv", ["initialize_method_packets.py", str(input_path), "--output-dir", str(output_dir)]):
                    self.assertEqual(initialize_method_packets.main(), 0)
            drafts = [json.loads(path.read_text(encoding="utf-8")) for path in output_dir.glob("*.draft.json")]
            self.assertEqual(len(drafts), 9)
            hashes = {item["method_analysis"]["method_input_sha256"] for item in drafts}
            self.assertEqual(len(hashes), 1)
            self.assertTrue(all(len(item["method_analysis"]["domain_assessments"]) == 8 for item in drafts))

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
