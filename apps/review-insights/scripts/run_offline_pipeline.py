"""Manual offline pipeline runner for one Steam appid."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR / "backend"
REPO_ROOT = APP_DIR.parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pipeline.offline_pipeline import run_offline_pipeline_for_appid


def _load_env() -> None:
    """Load environment variables from common .env locations."""
    for path in (REPO_ROOT / ".env", APP_DIR / ".env"):
        if path.exists():
            load_dotenv(dotenv_path=path, override=False)


def _print_precheck(*, use_llm_fallback: bool) -> None:
    """Print one-line runtime precheck for LLM settings."""
    key_status = "set" if bool(os.getenv("OPENAI_API_KEY")) else "missing"
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    print(
        f"[offline-pipeline] precheck: llm_requested={use_llm_fallback} "
        f"openai_key={key_status} model={model}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline ingestion + preprocessing + analysis for one appid."
    )
    parser.add_argument("--appid", type=int, required=True, help="Steam appid")
    parser.add_argument(
        "--review-pages",
        default="all",
        help="all 또는 1~200 정수",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="결과 저장 루트 디렉터리(기본: apps/review-insights/data)",
    )
    parser.add_argument(
        "--use-llm-fallback",
        action="store_true",
        help="애매한 리뷰 subset에 대해서만 LLM fallback 사용",
    )
    parser.add_argument(
        "--max-llm-reviews",
        type=int,
        default=50,
        help="LLM fallback 최대 호출 리뷰 수",
    )
    parser.add_argument(
        "--llm-timeout-seconds",
        type=int,
        default=20,
        help="LLM 1회 호출 timeout(초)",
    )
    parser.add_argument(
        "--llm-retry-limit",
        type=int,
        default=2,
        help="LLM 호출 재시도 횟수",
    )
    parser.add_argument(
        "--llm-min-confidence",
        type=float,
        default=0.70,
        help="이 값 미만 confidence는 rule 결과 유지",
    )
    parser.add_argument(
        "--game-name",
        default=None,
        help="Steam 게임명이 비어 있을 때만 파일명에 사용할 보조 이름(선택)",
    )
    return parser.parse_args()


def main() -> int:
    _load_env()
    args = parse_args()
    _print_precheck(use_llm_fallback=bool(args.use_llm_fallback))
    try:
        summary = run_offline_pipeline_for_appid(
            args.appid,
            data_root=args.data_root if args.data_root else APP_DIR / "data",
            review_pages=args.review_pages,
            use_llm_fallback=bool(args.use_llm_fallback),
            max_llm_reviews=args.max_llm_reviews,
            llm_timeout_seconds=args.llm_timeout_seconds,
            llm_retry_limit=args.llm_retry_limit,
            llm_min_confidence=args.llm_min_confidence,
            game_name=args.game_name,
            log_fetch_progress=True,
        )
    except Exception as exc:  # pragma: no cover - CLI surface.
        print(f"[offline-pipeline] failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI surface.
    raise SystemExit(main())
