"""Comparison helpers for review-insights results."""

from __future__ import annotations

from typing import Any


def compare_analysis_results(
    appid1: int,
    analysis1: dict[str, Any],
    raw_reviews1: list[dict[str, Any]],
    metadata1: dict[str, Any] | None,
    appid2: int,
    analysis2: dict[str, Any],
    raw_reviews2: list[dict[str, Any]],
    metadata2: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a conservative comparison payload for two analyzed games."""
    status, reason, warnings = determine_comparison_status(
        appid1,
        analysis1,
        len(raw_reviews1),
        metadata1,
        appid2,
        analysis2,
        len(raw_reviews2),
        metadata2,
    )

    categories1 = set((analysis1.get("issue_signals") or {}).keys())
    categories2 = set((analysis2.get("issue_signals") or {}).keys())

    shared_categories = sorted(categories1 & categories2)
    unique_to_game_1 = sorted(categories1 - categories2)
    unique_to_game_2 = sorted(categories2 - categories1)

    return {
        "appid1": appid1,
        "appid2": appid2,
        "comparison_status": status,
        "comparison_reason": reason,
        "warnings": warnings,
        "shared_issue_categories": shared_categories,
        "unique_to_game_1": unique_to_game_1,
        "unique_to_game_2": unique_to_game_2,
        "comparison_summary": build_comparison_summary(
            appid1,
            analysis1,
            metadata1,
            appid2,
            analysis2,
            metadata2,
            status,
        ),
        "game_1": {
            "appid": appid1,
            "sample_size_tier": analysis1.get("sample_size_tier"),
            "trend_status": analysis1.get("trend_status"),
            "issue_count": len(categories1),
            "metadata": metadata1 or {},
        },
        "game_2": {
            "appid": appid2,
            "sample_size_tier": analysis2.get("sample_size_tier"),
            "trend_status": analysis2.get("trend_status"),
            "issue_count": len(categories2),
            "metadata": metadata2 or {},
        },
    }


def determine_comparison_status(
    appid1: int,
    analysis1: dict[str, Any],
    raw_count1: int,
    metadata1: dict[str, Any] | None,
    appid2: int,
    analysis2: dict[str, Any],
    raw_count2: int,
    metadata2: dict[str, Any] | None,
) -> tuple[str, str, list[str]]:
    """Return a conservative comparison status based on available signals and metadata."""
    warnings = [
        "이 비교는 리뷰 패턴 차이를 보여주며, 제품 우열을 단정하지 않습니다.",
    ]

    if appid1 == appid2:
        warnings.append("같은 게임끼리 비교하고 있으므로 기준선 확인용으로만 해석합니다.")
        return "comparable", "same_appid", warnings

    tier1 = analysis1.get("sample_size_tier", "empty")
    tier2 = analysis2.get("sample_size_tier", "empty")
    if tier1 in {"empty", "very_small"} or tier2 in {"empty", "very_small"}:
        warnings.append("한쪽 또는 양쪽의 표본이 매우 작아 직접 비교를 제한합니다.")
        return "not_comparable", "insufficient_sample", warnings

    if raw_count1 == 0 or raw_count2 == 0:
        warnings.append("한쪽 또는 양쪽에 raw 리뷰가 없어 비교할 수 없습니다.")
        return "not_comparable", "missing_raw_reviews", warnings

    if not metadata1 or not metadata2:
        warnings.append("게임 메타데이터가 부족해 보수적으로 비교합니다.")
        return "compare_with_caution", "metadata_not_available", warnings

    stage1 = str(metadata1.get("release_stage") or "unknown")
    stage2 = str(metadata2.get("release_stage") or "unknown")
    if stage1 != stage2 and {stage1, stage2} & {"early_access", "coming_soon"}:
        warnings.append("출시 단계가 달라 직접 비교에 적합하지 않습니다.")
        return "not_comparable", "release_stage_mismatch", warnings

    genres1 = _normalized_genres(metadata1)
    genres2 = _normalized_genres(metadata2)
    if genres1 and genres2 and not (genres1 & genres2):
        warnings.append("장르가 크게 달라 해석에 주의가 필요합니다.")
        return "compare_with_caution", "genre_mismatch", warnings

    price1 = str(metadata1.get("price_model") or "unknown")
    price2 = str(metadata2.get("price_model") or "unknown")
    if price1 != "unknown" and price2 != "unknown" and price1 != price2:
        warnings.append("가격 모델이 달라 비교 결과를 조심해서 해석해야 합니다.")
        return "compare_with_caution", "price_model_mismatch", warnings

    volume_ratio = max(raw_count1, raw_count2) / max(min(raw_count1, raw_count2), 1)
    if volume_ratio >= 5:
        warnings.append("두 게임의 리뷰 규모 차이가 커서 해석에 주의가 필요합니다.")
        return "compare_with_caution", "large_volume_gap", warnings

    warnings.append("장르, 가격 모델, 출시 단계가 크게 어긋나지 않아 비교를 허용합니다.")
    return "comparable", "aligned_metadata", warnings


def build_comparison_summary(
    appid1: int,
    analysis1: dict[str, Any],
    metadata1: dict[str, Any] | None,
    appid2: int,
    analysis2: dict[str, Any],
    metadata2: dict[str, Any] | None,
    comparison_status: str,
) -> str:
    """Create a short comparison summary for the dashboard and API."""
    categories1 = set((analysis1.get("issue_signals") or {}).keys())
    categories2 = set((analysis2.get("issue_signals") or {}).keys())
    shared = sorted(categories1 & categories2)

    game_1_name = _display_name(appid1, metadata1)
    game_2_name = _display_name(appid2, metadata2)

    if comparison_status == "not_comparable":
        return (
            f"{game_1_name}와 {game_2_name}는 현재 표본 또는 메타데이터 조건에서 "
            "직접 비교에 적합하지 않습니다."
        )

    if not shared:
        return (
            f"{game_1_name}와 {game_2_name}는 공통으로 반복되는 이슈 카테고리가 적어 "
            "패턴 차이 중심으로 해석하는 편이 안전합니다."
        )

    joined = ", ".join(shared[:3])
    return (
        f"{game_1_name}와 {game_2_name} 모두 {joined} 관련 신호가 보입니다. "
        "다만 강도 차이는 각 게임의 표본과 대표 리뷰를 함께 확인해야 합니다."
    )


def _display_name(appid: int, metadata: dict[str, Any] | None) -> str:
    if metadata and metadata.get("name"):
        return str(metadata["name"])
    return f"appid {appid}"


def _normalized_genres(metadata: dict[str, Any]) -> set[str]:
    return {
        str(genre).strip().lower()
        for genre in (metadata.get("genres") or [])
        if str(genre).strip()
    }
