"""Tests for consumer report evidence block structure."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.report_view import build_consumer_report_from_snapshot


def sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[.!?。！？]+", text) if part.strip()]
    return len(parts)


class ReportViewTests(unittest.TestCase):
    def test_evidence_reviews_are_grouped_insight_blocks(self):
        metadata = {
            "appid": 2456740,
            "name": "inZOI (인조이)",
            "genres": ["Simulation"],
            "release_stage": "released",
        }
        analysis = {
            "issue_signals": {
                "performance": {
                    "mention_count": 120,
                    "negative_ratio": 0.82,
                    "recent_trend": "up",
                    "themes": ["프레임 드랍", "최적화 문제"],
                    "sample_reviews": ["전투 중 프레임이 크게 떨어져서 몰입이 끊깁니다."],
                },
                "customization": {
                    "mention_count": 95,
                    "negative_ratio": 0.21,
                    "recent_trend": "flat",
                    "themes": ["커스터마이징 호평"],
                    "sample_reviews": ["커스터마이징 폭이 넓어서 만드는 재미가 큽니다."],
                },
            }
        }
        processed = [
            {
                "review_id": "r1",
                "review_text": (
                    "전투 중 프레임이 갑자기 끊겨 몰입이 깨집니다. "
                    "중요한 타이밍마다 반응이 늦게 들어와서 답답합니다."
                ),
                "included_in_analysis": True,
                "category_tags": ["performance"],
                "voted_up": False,
            },
            {
                "review_id": "r2",
                "review_text": (
                    "프레임 드랍 때문에 조작이 밀리는 느낌이 납니다. "
                    "전투 흐름이 자꾸 끊겨 스트레스를 받습니다."
                ),
                "included_in_analysis": True,
                "category_tags": ["performance"],
                "voted_up": False,
            },
            {
                "review_id": "r3",
                "review_text": (
                    "외형 커스터마이징이 다양해서 캐릭터 만드는 재미가 큽니다. "
                    "꾸미는 과정이 만족스럽습니다."
                ),
                "included_in_analysis": True,
                "category_tags": ["customization"],
                "voted_up": True,
            },
            {
                "review_id": "r4",
                "review_text": (
                    "커스터마이징 선택지가 많아서 오래 만지게 됩니다. "
                    "취향대로 꾸밀 수 있는 점이 정말 좋습니다."
                ),
                "included_in_analysis": True,
                "category_tags": ["customization"],
                "voted_up": True,
            },
        ]

        report = build_consumer_report_from_snapshot(
            appid=2456740,
            metadata=metadata,
            analysis=analysis,
            processed_reviews=processed,
            pipeline_run_id="test-run",
            source_review_count=4,
        )

        evidence_blocks = report.get("evidence_reviews", [])
        self.assertTrue(evidence_blocks)
        for block in evidence_blocks:
            self.assertIn("title", block)
            self.assertIn("explanation", block)
            self.assertIn("stance", block)
            self.assertIn("consensus_level", block)
            self.assertIn("mention_count", block)
            self.assertIn("evidence_snippets", block)
            self.assertIn(block["stance"], {"positive", "negative"})
            self.assertEqual(block["consensus_level"], "high")
            self.assertGreaterEqual(len(block["evidence_snippets"]), 2)
            self.assertLessEqual(len(block["evidence_snippets"]), 3)
            for snippet in block["evidence_snippets"]:
                self.assertGreaterEqual(sentence_count(snippet), 1)
                self.assertLessEqual(sentence_count(snippet), 4)
                self.assertFalse(snippet.endswith("…"))

        evidence_sections = report.get("evidence_sections")
        self.assertIsInstance(evidence_sections, dict)
        self.assertIn("loved", evidence_sections)
        self.assertIn("complained", evidence_sections)
        self.assertTrue(evidence_sections["loved"])
        self.assertTrue(evidence_sections["complained"])
        self.assertTrue(all(block.get("stance") == "positive" for block in evidence_sections["loved"]))
        self.assertTrue(
            all(block.get("stance") == "negative" for block in evidence_sections["complained"])
        )


if __name__ == "__main__":
    unittest.main()
