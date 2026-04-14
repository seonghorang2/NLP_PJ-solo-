"""Tests for read-only user routes and admin-only ingest helpers."""

from __future__ import annotations

import json
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
    list_demo_games,
    load_analysis_result,
    load_game_metadata,
    load_processed_reviews,
    load_raw_reviews,
    load_report,
    run_admin_ingest,
)
from storage.file_store import FileStore


def write_demo_catalog(root: Path, appids: list[int]) -> None:
    catalog_dir = root / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {"appid": appid, "name": f"Game {appid}", "enabled_for_demo": True}
        for appid in appids
    ]
    (catalog_dir / "demo_games.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_snapshot_files(root: Path, appid: int) -> None:
    store = FileStore(root)
    store.write_analysis_result(
        appid,
        {
            "appid": appid,
            "sample_size_tier": "medium",
            "trend_status": "ready",
            "warnings": [],
            "issue_signals": {
                "performance": {
                    "mention_count": 20,
                    "negative_ratio": 0.7,
                    "recent_trend": "up",
                    "experienced_player_share": 0.8,
                    "themes": ["최적화 문제"],
                    "sample_reviews": ["업데이트 이후 프레임 드랍이 심해졌습니다."],
                },
                "gameplay": {
                    "mention_count": 25,
                    "negative_ratio": 0.2,
                    "recent_trend": "flat",
                    "experienced_player_share": 0.7,
                    "themes": ["전투 손맛"],
                    "sample_reviews": ["전투가 재밌어서 계속 하게 됩니다."],
                },
            },
            "summary": {},
        },
        game_name=f"Game {appid}",
    )
    store.write_game_metadata(
        appid,
        {
            "appid": appid,
            "name": f"Game {appid}",
            "genres": ["Action"],
            "release_stage": "released",
        },
        game_name=f"Game {appid}",
    )
    store.write_raw_reviews(
        appid,
        [{"review_id": "1", "appid": appid, "review_text": "raw"}],
        game_name=f"Game {appid}",
    )
    store.write_processed_reviews(
        appid,
        [
            {
                "review_id": "1",
                "appid": appid,
                "review_text": "전투는 재밌지만 프레임이 불안정합니다.",
                "voted_up": False,
                "included_in_analysis": True,
                "category_tags": ["performance", "gameplay"],
                "playtime_at_review_hours": 12.3,
            }
        ],
        game_name=f"Game {appid}",
    )


class ApiFlowTests(unittest.TestCase):
    def tearDown(self):
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def test_list_demo_games_returns_predefined_catalog_only(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740, 1049590])
        write_snapshot_files(TEST_OUTPUT_DIR, 2456740)

        games = list_demo_games(data_root=TEST_OUTPUT_DIR)

        self.assertEqual([game["appid"] for game in games], [1049590, 2456740])
        self.assertFalse(games[0]["report_ready"])
        self.assertTrue(games[1]["report_ready"])

    def test_load_report_returns_stored_consumer_report_when_available(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740])
        write_snapshot_files(TEST_OUTPUT_DIR, 2456740)
        store = FileStore(TEST_OUTPUT_DIR)
        store.write_report_view(
            2456740,
            {
                "headline": "테스트 헤드라인",
                "buy_recommendation": "buy_now",
                "buy_timing_summary": "지금 구매해도 괜찮습니다.",
                "good_for": ["A"],
                "not_good_for": ["B"],
                "top_strengths": [],
                "top_risks": [],
                "recent_state": {"status": "stable", "summary": "안정"},
                "evidence_reviews": [],
            },
            game_name="Game 2456740",
        )

        report = load_report(2456740, data_root=TEST_OUTPUT_DIR)

        self.assertEqual(report["headline"], "테스트 헤드라인")
        self.assertEqual(report["buy_recommendation"], "buy_now")

    def test_load_report_builds_from_snapshot_without_running_analysis(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740])
        write_snapshot_files(TEST_OUTPUT_DIR, 2456740)

        with patch("api.routes.run_offline_pipeline_for_appid") as run_pipeline:
            report = load_report(2456740, data_root=TEST_OUTPUT_DIR)
            run_pipeline.assert_not_called()

        self.assertIn("headline", report)
        self.assertIn("buy_recommendation", report)
        self.assertIn("top_risks", report)
        self.assertIn("top_strengths", report)

    def test_user_read_helpers_reject_non_demo_appid(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740])
        write_snapshot_files(TEST_OUTPUT_DIR, 2456740)

        with self.assertRaises(ValueError):
            load_report(999999, data_root=TEST_OUTPUT_DIR)
        with self.assertRaises(ValueError):
            load_analysis_result(999999, data_root=TEST_OUTPUT_DIR)
        with self.assertRaises(ValueError):
            load_game_metadata(999999, data_root=TEST_OUTPUT_DIR)
        with self.assertRaises(ValueError):
            load_raw_reviews(999999, data_root=TEST_OUTPUT_DIR)
        with self.assertRaises(ValueError):
            load_processed_reviews(999999, data_root=TEST_OUTPUT_DIR)

    def test_admin_ingest_uses_offline_pipeline_entrypoint(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740])

        with patch("api.routes.run_offline_pipeline_for_appid") as run_pipeline:
            run_pipeline.return_value = {"appid": 2456740, "pipeline_run_id": "run-1"}
            result = run_admin_ingest(
                {"appid": 2456740, "review_pages": 4, "use_llm_fallback": False},
                data_root=TEST_OUTPUT_DIR,
            )

        self.assertEqual(result["appid"], 2456740)
        run_pipeline.assert_called_once()

    def test_admin_ingest_rejects_non_demo_appid(self):
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_demo_catalog(TEST_OUTPUT_DIR, [2456740])

        with self.assertRaises(ValueError):
            run_admin_ingest({"appid": 1049590}, data_root=TEST_OUTPUT_DIR)


if __name__ == "__main__":
    unittest.main()
