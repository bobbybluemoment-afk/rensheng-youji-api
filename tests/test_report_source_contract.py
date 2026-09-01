from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.audit_report_source_contract import audit as audit_contract
from scripts.audit_claim_diversity import audit as audit_diversity
from scripts.build_report_source_bundle import build
from scripts.core_baseline import validate_quality_audit
from scripts.report_source_contract import mandatory_candidate_bounds


class ReportSourceContractTest(unittest.TestCase):
    def test_repository_contract_is_closed_across_stages(self) -> None:
        self.assertEqual(audit_contract(ROOT), [])

    def test_sparse_current_stage_source_keeps_one_candidate(self) -> None:
        analysis = {
            "report_claim_ledger": [{
                "claim_id": "current-1",
                "domain": "career",
                "origin": "timing_baseline",
                "report_role": "primary",
                "calibration_status": "unverified",
                "confidence": "high",
                "coverage_tags": ["current_change"],
                "plain_claim": "当前阶段更需要把已经完成的成果正式记录下来。",
                "mechanism_family": "timing",
                "allowed_examples": [],
            }],
            "formation_chains": [],
            "domain_linkage_chains": [],
        }
        source = build(analysis)["current_stage_source"]
        self.assertEqual(source["mandatory_candidate_ids"], ["current-1"])
        self.assertEqual(mandatory_candidate_bounds(source["claim_ids"]), (1, 2))

    def test_quality_audit_accepts_sparse_domains_and_one_current_candidate(self) -> None:
        domains = ["self_growth", "love_partner", "career", "finance_resources", "body_emotion", "family_growth"]
        sentences = [
            "你做决定前会先确认自己真正需要解决的问题。",
            "当外部要求变化时，你会重新划定可以接受的边界。",
            "你开始关系时看重回应是否稳定而不是承诺是否漂亮。",
            "长期相处中，你需要双方能够讨论具体的时间安排。",
            "你更适合负责需要持续推进并留下正式结果的任务。",
            "职责增加时，你需要同步确认评价方式和实际权限。",
            "你的收入积累更依赖可持续回报而不是短期机会。",
            "涉及合作分配时，提前写清范围能减少后续损耗。",
            "压力刚出现时你仍能行动，疲劳通常稍后才被注意。",
            "恢复精力需要先结束持续回应他人的工作状态。",
            "接受家庭帮助时，你也会衡量它是否影响决定权。",
            "建立独立生活后，你仍可能以实际行动回馈亲友。",
        ]
        claims = []
        dimensions = {}
        for domain_index, domain in enumerate(domains):
            domain_ids = []
            for offset in range(2):
                index = domain_index * 2 + offset
                claim_id = f"{domain}-{offset + 1}"
                domain_ids.append(claim_id)
                claims.append({
                    "claim_id": claim_id,
                    "domain": domain,
                    "claim_family": f"family-{domain_index}",
                    "mechanism_family": f"mechanism-{domain_index}",
                    "reality_dimension": f"axis-{offset + 1}",
                    "new_information": f"{domain}-new-{offset + 1}",
                    "plain_claim": sentences[index],
                    "claim": sentences[index],
                })
            dimensions[domain] = {"claim_ids": domain_ids, "mandatory_candidate_ids": domain_ids[:1]}
        data = {
            "report_claim_ledger": claims,
            "report_source_bundle": {
                "life_narrative_source": {"claim_ids": [claims[0]["claim_id"], claims[2]["claim_id"]], "mandatory_candidate_ids": [claims[0]["claim_id"]]},
                "current_stage_source": {"claim_ids": [claims[4]["claim_id"]], "mandatory_candidate_ids": [claims[4]["claim_id"]]},
                "dimensions": dimensions,
            },
        }
        self.assertEqual(audit_diversity(data), [])

    def test_quality_receipt_must_match_core_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            directory = Path(temp_dir)
            source = directory / "analysis-output-initial.json"
            receipt = directory / "core-quality-audit.json"
            source.write_text('{"analysis_meta":{"analysis_id":"a"}}', encoding="utf-8")
            receipt.write_text(json.dumps({
                "schema_version": "1.0.0",
                "status": "ok",
                "analysis_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "errors": [],
            }), encoding="utf-8")
            validate_quality_audit(source, receipt)
            source.write_text('{"analysis_meta":{"analysis_id":"changed"}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                validate_quality_audit(source, receipt)


if __name__ == "__main__":
    unittest.main()
