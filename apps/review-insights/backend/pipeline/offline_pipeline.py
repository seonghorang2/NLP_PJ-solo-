"""Offline-only ingestion and analysis entrypoint."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.llm_fallback import (
    LLMFallbackConfig,
    apply_selective_llm_fallback,
)
from analysis.preprocess import preprocess_reviews
from models.schemas import RawReview
from services.analysis_service import (
    build_analysis_result_from_processed,
    enrich_processed_reviews,
)
from services.llm_classifier import OpenAILLMClassifier
from services.report_view import build_report_ready_data
from services.steam_reviews import (
    fetch_steam_game_metadata,
    fetch_steam_reviews,
    normalize_steam_game_metadata,
    normalize_steam_reviews,
)
from storage.file_store import FileStore

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = APP_ROOT / "data"
MAX_NUMERIC_REVIEW_PAGES = 200


def run_offline_pipeline_for_appid(
    appid: int,
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    review_pages: int | str = "all",
    use_llm_fallback: bool = True,
    max_llm_reviews: int = 50,
    llm_timeout_seconds: int = 20,
    llm_retry_limit: int = 2,
    llm_min_confidence: float = 0.70,
    game_name: str | None = None,
) -> dict[str, Any]:
    """Run full offline pipeline for one appid and persist artifacts."""
    parsed_pages = _parse_review_pages(review_pages)
    pipeline_run_id = f"{appid}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    steam_payload = fetch_steam_reviews(
        appid,
        max_pages=None if parsed_pages == "all" else parsed_pages,
    )
    fetch_stats = steam_payload.get("_fetch_stats", {}) if isinstance(steam_payload, dict) else {}
    metadata_payload = fetch_steam_game_metadata(appid)

    metadata = normalize_steam_game_metadata(appid, metadata_payload)
    output_game_name = game_name or metadata.name

    raw_reviews: list[RawReview] = normalize_steam_reviews(appid, steam_payload)
    deterministic_processed = preprocess_reviews(raw_reviews)

    llm_stats = {
        "considered": 0,
        "invoked": 0,
        "success": 0,
        "schema_invalid": 0,
        "low_confidence": 0,
        "cache_hits": 0,
        "skipped_hard_exclusion": 0,
        "skipped_no_semantic_signal": 0,
        "skipped_no_uncertainty_signal": 0,
    }

    processed_reviews = list(deterministic_processed)
    if use_llm_fallback:
        llm_config = LLMFallbackConfig(
            enabled=True,
            max_llm_reviews=max_llm_reviews,
            timeout_seconds=llm_timeout_seconds,
            retry_limit=llm_retry_limit,
            min_confidence=llm_min_confidence,
        )
        classifier = OpenAILLMClassifier()
        processed_reviews, stats = apply_selective_llm_fallback(
            processed_reviews,
            classifier=classifier,
            config=llm_config,
        )
        llm_stats = stats.to_dict()

    processed_reviews = enrich_processed_reviews(processed_reviews)
    analysis = build_analysis_result_from_processed(processed_reviews, appid=appid)

    analysis_payload = analysis.to_dict()
    analysis_payload.update(
        {
            "pipeline_run_id": pipeline_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_review_count": len(raw_reviews),
            "review_pages": parsed_pages,
            "fetched_pages": fetch_stats.get("pages_fetched"),
            "fetched_review_count": fetch_stats.get("deduped_review_count"),
            "fetch_timeout_seconds": fetch_stats.get("request_timeout_seconds"),
            "fetch_filter": fetch_stats.get("filter_type"),
            "all_mode_page_cap": fetch_stats.get("all_mode_page_cap"),
            "all_mode_cap_reached": fetch_stats.get("all_mode_cap_reached"),
            "llm_stats": llm_stats,
        }
    )

    report_view = build_report_ready_data(
        appid=appid,
        metadata=metadata,
        analysis=analysis,
        raw_reviews=raw_reviews,
        processed_reviews=processed_reviews,
        pipeline_run_id=pipeline_run_id,
    )

    store = FileStore(data_root)
    store.write_raw_reviews(
        appid,
        [review.to_dict() for review in raw_reviews],
        game_name=output_game_name,
    )
    store.write_processed_reviews(
        appid,
        [review.to_dict() for review in processed_reviews],
        game_name=output_game_name,
    )
    store.write_analysis_result(
        appid,
        analysis_payload,
        game_name=output_game_name,
    )
    store.write_game_metadata(
        appid,
        metadata.to_dict(),
        game_name=output_game_name,
    )
    store.write_report_view(
        appid,
        report_view,
        game_name=output_game_name,
    )

    return {
        "appid": appid,
        "pipeline_run_id": pipeline_run_id,
        "raw_review_count": len(raw_reviews),
        "processed_review_count": len(processed_reviews),
        "included_review_count": sum(
            1 for review in processed_reviews if review.included_in_analysis
        ),
        "review_pages": parsed_pages,
        "llm_stats": llm_stats,
        "output_file_game_name": output_game_name,
    }


def _parse_review_pages(value: Any) -> int | str:
    if value is None:
        return "all"

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "all":
            return "all"
        if normalized.isdigit():
            value = int(normalized)
        else:
            raise ValueError(
                f"review_pages must be 'all' or an integer between 1 and {MAX_NUMERIC_REVIEW_PAGES}."
            )

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"review_pages must be 'all' or an integer between 1 and {MAX_NUMERIC_REVIEW_PAGES}."
        )
    if value < 1 or value > MAX_NUMERIC_REVIEW_PAGES:
        raise ValueError(
            f"review_pages must be 'all' or an integer between 1 and {MAX_NUMERIC_REVIEW_PAGES}."
        )
    return value
