from __future__ import annotations

import unittest

from scripts.report_source_contract import synthesis_disposition_gaps


class V223CoreDepthContractTest(unittest.TestCase):
    def test_every_method_hypothesis_needs_an_explicit_core_disposition(self) -> None:
        data = {
            "independent_method_analyses": [{
                "method_id": "pattern_structure",
                "status": "complete",
                "reality_hypotheses": [
                    {"hypothesis_id": "h1"},
                    {"hypothesis_id": "h2"},
                ],
            }],
            "method_synthesis": {"clusters": [{
                "synthesis_id": "s1",
                "member_hypothesis_ids": ["h1", "h2"],
                "report_role": "supplemental",
            }]},
            "report_claim_ledger": [{
                "claim_id": "c1",
                "synthesis_ids": ["s1"],
                "method_hypothesis_ids": ["h1"],
            }],
        }
        gaps = synthesis_disposition_gaps(data)
        self.assertTrue(any("h2" in item and "静默压缩" in item for item in gaps))

        data["report_claim_ledger"][0]["method_hypothesis_ids"].append("h2")
        self.assertEqual(synthesis_disposition_gaps(data), [])

    def test_excluded_cluster_is_a_valid_internal_disposition(self) -> None:
        data = {
            "independent_method_analyses": [{
                "method_id": "pattern_structure",
                "status": "complete",
                "reality_hypotheses": [{"hypothesis_id": "h1"}],
            }],
            "method_synthesis": {"clusters": [{
                "synthesis_id": "s1",
                "member_hypothesis_ids": ["h1"],
                "report_role": "excluded",
            }]},
            "report_claim_ledger": [],
        }
        self.assertEqual(synthesis_disposition_gaps(data), [])


if __name__ == "__main__":
    unittest.main()
