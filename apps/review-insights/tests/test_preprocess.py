"""Tests for deterministic preprocessing rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from analysis.preprocess import preprocess_review
from models.schemas import RawReview


def make_raw_review(review_text: str) -> RawReview:
    return RawReview(
        review_id="review-1",
        appid=570,
        review_text=review_text,
        voted_up=False,
        timestamp_created=0,
        timestamp_updated=0,
        playtime_forever=120.0,
        playtime_at_review_hours=2.0,
        num_reviews=3,
        author_steamid="steamid-1",
    )


class PreprocessReviewTests(unittest.TestCase):
    def test_includes_korean_feedback_review(self):
        review = preprocess_review(
            make_raw_review("그래픽은 좋은데 최적화가 안 좋아 프레임이 자주 떨어짐")
        )

        self.assertTrue(review.included_in_analysis)
        self.assertEqual(review.rule_decision, "include")

    def test_excludes_non_korean_review(self):
        review = preprocess_review(
            make_raw_review("matchmaking is broken and the server crashes every night")
        )

        self.assertFalse(review.included_in_analysis)
        self.assertEqual(review.rule_decision, "exclude_non_korean")

    def test_excludes_low_quality_review(self):
        review = preprocess_review(make_raw_review("짱"))

        self.assertFalse(review.included_in_analysis)
        self.assertTrue(review.is_low_quality)
        self.assertEqual(review.rule_decision, "exclude_low_quality")

    def test_excludes_profanity_only_review(self):
        review = preprocess_review(make_raw_review("쓰레기 망겜"))

        self.assertFalse(review.included_in_analysis)
        self.assertTrue(review.is_profanity_only)
        self.assertEqual(review.rule_decision, "exclude_low_quality")

    def test_keeps_profane_but_meaningful_feedback(self):
        review = preprocess_review(
            make_raw_review("쓰레기 같은 최적화 때문에 프레임이 계속 떨어짐")
        )

        self.assertTrue(review.included_in_analysis)
        self.assertFalse(review.is_profanity_only)
        self.assertIn("ambiguous_profanity", review.ambiguity_flags)

    def test_flags_ambiguous_review(self):
        review = preprocess_review(
            make_raw_review("그래픽은 좋은데 조작은 별로여서 좀 애매함")
        )

        self.assertTrue(review.included_in_analysis)
        self.assertIn("ambiguous_sentiment", review.ambiguity_flags)

    def test_flags_included_but_unclassified_review(self):
        review = preprocess_review(
            make_raw_review("이 게임은 진짜 완벽하네")
        )

        self.assertTrue(review.included_in_analysis)
        self.assertEqual(review.rule_decision, "include")
        self.assertEqual(review.category_tags, [])
        self.assertIn("unclassified_included", review.ambiguity_flags)


if __name__ == "__main__":
    unittest.main()
