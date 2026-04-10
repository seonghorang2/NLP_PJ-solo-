"""Tests for conservative game comparison logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.comparison_service import compare_analysis_results, determine_comparison_status


def make_analysis_payload(sample_size_tier: str, categories: list[str]) -> dict:
    return {
        "appid": 0,
        "sample_size_tier": sample_size_tier,
        "trend_status": "limited",
        "issue_signals": {category: {"mention_count": 1} for category in categories},
        "warnings": [],
    }


def make_metadata(
    *,
    name: str,
    genres: list[str],
    price_model: str = "paid",
    release_stage: str = "released",
) -> dict:
    return {
        "name": name,
        "genres": genres,
        "price_model": price_model,
        "release_stage": release_stage,
    }


class ComparisonServiceTests(unittest.TestCase):
    def test_determine_comparison_status_blocks_very_small_samples(self):
        status, reason, warnings = determine_comparison_status(
            570,
            make_analysis_payload("very_small", ["performance"]),
            5,
            make_metadata(name="A", genres=["Action"]),
            730,
            make_analysis_payload("small", ["bugs"]),
            20,
            make_metadata(name="B", genres=["Action"]),
        )

        self.assertEqual(status, "not_comparable")
        self.assertEqual(reason, "insufficient_sample")
        self.assertTrue(warnings)

    def test_determine_comparison_status_warns_on_large_volume_gap(self):
        status, reason, _warnings = determine_comparison_status(
            570,
            make_analysis_payload("small", ["performance"]),
            10,
            make_metadata(name="A", genres=["Action"]),
            730,
            make_analysis_payload("small", ["performance", "bugs"]),
            80,
            make_metadata(name="B", genres=["Action"]),
        )

        self.assertEqual(status, "compare_with_caution")
        self.assertEqual(reason, "large_volume_gap")

    def test_determine_comparison_status_blocks_release_stage_mismatch(self):
        status, reason, warnings = determine_comparison_status(
            570,
            make_analysis_payload("small", ["performance"]),
            20,
            make_metadata(name="A", genres=["Action"], release_stage="early_access"),
            730,
            make_analysis_payload("small", ["performance", "bugs"]),
            24,
            make_metadata(name="B", genres=["Action"], release_stage="released"),
        )

        self.assertEqual(status, "not_comparable")
        self.assertEqual(reason, "release_stage_mismatch")
        self.assertTrue(warnings)

    def test_determine_comparison_status_becomes_comparable_when_metadata_aligns(self):
        status, reason, warnings = determine_comparison_status(
            570,
            make_analysis_payload("small", ["performance"]),
            20,
            make_metadata(name="A", genres=["Action", "RPG"]),
            730,
            make_analysis_payload("small", ["performance", "bugs"]),
            24,
            make_metadata(name="B", genres=["Action"]),
        )

        self.assertEqual(status, "comparable")
        self.assertEqual(reason, "aligned_metadata")
        self.assertTrue(warnings)

    def test_compare_analysis_results_returns_shared_unique_and_metadata(self):
        comparison = compare_analysis_results(
            570,
            make_analysis_payload("small", ["performance", "graphics"]),
            [{"review_id": "1"}] * 12,
            make_metadata(name="Game A", genres=["Action"]),
            730,
            make_analysis_payload("small", ["performance", "bugs"]),
            [{"review_id": "2"}] * 14,
            make_metadata(name="Game B", genres=["Action"]),
        )

        self.assertEqual(comparison["comparison_status"], "comparable")
        self.assertEqual(comparison["shared_issue_categories"], ["performance"])
        self.assertEqual(comparison["unique_to_game_1"], ["graphics"])
        self.assertEqual(comparison["unique_to_game_2"], ["bugs"])
        self.assertEqual(comparison["game_1"]["metadata"]["name"], "Game A")


if __name__ == "__main__":
    unittest.main()
