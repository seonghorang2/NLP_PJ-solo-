"""Tests for API-facing ingestion and analysis helpers."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
TEST_OUTPUT_DIR = Path(__file__).resolve().parent / "_tmp_api_flow"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.routes import (
    ingest_reviews_payload,
    load_analysis_result,
    load_comparison_result,
    load_game_metadata,
    load_processed_reviews,
    load_raw_reviews,
)


def make_request_payload() -> dict:
    return {
        "appid": 570,
        "steam_payload": {
            "reviews": [
                {
                    "recommendationid": "1001",
                    "review": "최적화가 별로라 프레임 드랍이 심함",
                    "voted_up": False,
                    "timestamp_created": 1704067200,
                    "timestamp_updated": 1704067200,
                    "author": {
                        "steamid": "steamid-1001",
                        "playtime_forever": 180,
                        "playtime_at_review": 120,
                        "num_reviews": 4,
                    },
                },
                {
                    "recommendationid": "1002",
                    "review": "그래픽은 좋지만 조작이 답답하고 매칭이 느림",
                    "voted_up": False,
                    "timestamp_created": 1704672000,
                    "timestamp_updated": 1704672000,
                    "author": {
                        "steamid": "steamid-1002",
                        "playtime_forever": 240,
                        "playtime_at_review": 180,
                        "num_reviews": 2,
                    },
                },
            ]
        },
        "game_metadata_payload": {
            "570": {
                "success": True,
                "data": {
                    "steam_appid": 570,
                    "name": "Game 570",
                    "is_free": False,
                    "genres": [{"description": "Action"}],
                    "categories": [{"description": "Single-player"}],
                    "price_overview": {"currency": "KRW", "final": 22000},
                    "release_date": {"coming_soon": False, "date": "1 Jan, 2024"},
                },
            }
        },
    }


def make_second_payload() -> dict:
    return {
        "appid": 730,
        "steam_payload": {
            "reviews": [
                {
                    "recommendationid": "2001",
                    "review": "보스전에서 튕기고 저장이 안 됨",
                    "voted_up": False,
                    "timestamp_created": 1705276800,
                    "timestamp_updated": 1705276800,
                    "author": {
                        "steamid": "steamid-2001",
                        "playtime_forever": 300,
                        "playtime_at_review": 200,
                        "num_reviews": 8,
                    },
                }
            ]
        },
        "game_metadata_payload": {
            "730": {
                "success": True,
                "data": {
                    "steam_appid": 730,
                    "name": "Game 730",
                    "is_free": False,
                    "genres": [{"description": "Action"}],
                    "categories": [{"description": "Single-player"}],
                    "price_overview": {"currency": "KRW", "final": 18000},
                    "release_date": {"coming_soon": False, "date": "1 Jan, 2024"},
                },
            }
        },
    }


class ApiFlowTests(unittest.TestCase):
    def tearDown(self):
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def test_ingest_reviews_payload_persists_analysis_artifacts(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        response = ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)

        self.assertEqual(response["appid"], 570)
        self.assertEqual(response["raw_review_count"], 2)
        self.assertEqual(response["processed_review_count"], 2)
        self.assertEqual(response["included_review_count"], 2)
        self.assertEqual(response["price_model"], "paid")
        self.assertEqual(response["release_stage"], "released")

    def test_load_analysis_result_returns_saved_payload(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)

        analysis = load_analysis_result(570, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(analysis["appid"], 570)
        self.assertIn("issue_signals", analysis)
        self.assertIn("warnings", analysis)

    def test_load_raw_reviews_returns_saved_records(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)

        raw_reviews = load_raw_reviews(570, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(len(raw_reviews), 2)
        self.assertEqual(raw_reviews[0]["appid"], 570)
        self.assertIn("review_text", raw_reviews[0])

    def test_load_processed_reviews_returns_saved_records(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)

        processed_reviews = load_processed_reviews(570, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(len(processed_reviews), 2)
        self.assertEqual(processed_reviews[0]["appid"], 570)
        self.assertIn("included_in_analysis", processed_reviews[0])
        self.assertIn("category_tags", processed_reviews[0])

    def test_load_game_metadata_returns_saved_metadata(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)

        metadata = load_game_metadata(570, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(metadata["name"], "Game 570")
        self.assertEqual(metadata["price_model"], "paid")

    def test_ingest_reviews_payload_validates_request_shape(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with self.assertRaises(ValueError):
            ingest_reviews_payload({"appid": "570"}, data_root=TEST_OUTPUT_DIR)

        with self.assertRaises(ValueError):
            ingest_reviews_payload(
                {"appid": 570, "steam_payload": []},
                data_root=TEST_OUTPUT_DIR,
            )

        with self.assertRaises(ValueError):
            ingest_reviews_payload(
                {"appid": 570, "steam_payload": make_request_payload()["steam_payload"], "game_metadata_payload": []},
                data_root=TEST_OUTPUT_DIR,
            )

    def test_ingest_reviews_payload_can_fetch_from_steam_services_when_payload_missing(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with patch("api.routes.fetch_steam_reviews", return_value=make_request_payload()["steam_payload"]), patch(
            "api.routes.fetch_steam_game_metadata",
            return_value=make_request_payload()["game_metadata_payload"],
        ):
            response = ingest_reviews_payload({"appid": 570}, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(response["appid"], 570)
        self.assertEqual(response["raw_review_count"], 2)
        self.assertTrue(response["metadata_collected"])

    def test_load_comparison_result_returns_status_payload(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        ingest_reviews_payload(make_request_payload(), data_root=TEST_OUTPUT_DIR)
        ingest_reviews_payload(make_second_payload(), data_root=TEST_OUTPUT_DIR)

        comparison = load_comparison_result(570, 730, data_root=TEST_OUTPUT_DIR)

        self.assertIn("comparison_status", comparison)
        self.assertIn("comparison_reason", comparison)
        self.assertIn("comparison_summary", comparison)
        self.assertIn("metadata", comparison["game_1"])
        self.assertIn("metadata", comparison["game_2"])


if __name__ == "__main__":
    unittest.main()
