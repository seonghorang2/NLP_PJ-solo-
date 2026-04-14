"""Consumer-facing purchase decision report builders."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from models.schemas import AnalysisResult, GameMetadata, ProcessedReview, RawReview
from services.report_writer_llm import OpenAIReportWriter

REQUIRED_REPORT_KEYS = {
    "headline",
    "buy_recommendation",
    "buy_timing_summary",
    "good_for",
    "not_good_for",
    "top_strengths",
    "top_risks",
    "recent_state",
    "evidence_reviews",
}

CATEGORY_DISPLAY = {
    "balance": "밸런스",
    "performance": "성능/최적화",
    "bugs": "버그/안정성",
    "content_depth": "콘텐츠 볼륨",
    "difficulty": "진입 난이도",
    "difficulty_onboarding": "튜토리얼/초반 진입",
    "controls": "조작/UI",
    "matchmaking": "매칭/서버",
    "multiplayer": "멀티플레이",
    "localization": "번역/로컬라이징",
    "graphics": "그래픽/비주얼",
    "sound": "사운드",
    "gameplay": "전투/핵심 플레이",
    "story": "스토리/몰입",
    "customization": "커스터마이징",
    "building_ux": "건축/배치 UX",
    "save_progression": "저장/진행 안정성",
    "mod_support": "모드 지원/호환성",
}

GOOD_FOR_PHRASES = {
    "gameplay": "전투와 조작 손맛을 중시하는 플레이어",
    "story": "서사와 연출 몰입감을 중요하게 보는 플레이어",
    "graphics": "비주얼 완성도를 구매 기준으로 보는 플레이어",
    "customization": "캐릭터/빌드 커스터마이징을 즐기는 플레이어",
    "content_depth": "장시간 파고들 수 있는 성장 루프를 선호하는 플레이어",
    "difficulty": "학습 곡선이 있어도 숙련해 가는 재미를 좋아하는 플레이어",
}

NOT_GOOD_FOR_PHRASES = {
    "performance": "프레임 저하나 끊김에 민감한 플레이어",
    "bugs": "버그/충돌 허용 범위가 낮은 플레이어",
    "difficulty": "초반 진입장벽이 낮은 게임을 원하는 플레이어",
    "difficulty_onboarding": "튜토리얼 완성도가 중요한 플레이어",
    "save_progression": "진행 데이터 안정성을 최우선으로 보는 플레이어",
    "mod_support": "모드 생태계 활용을 핵심으로 생각하는 플레이어",
    "matchmaking": "멀티 매칭 안정성을 최우선으로 보는 플레이어",
    "multiplayer": "팀플레이 환경 품질에 민감한 플레이어",
    "balance": "메타/밸런스 변동에 스트레스를 크게 받는 플레이어",
}

NEGATIVE_THEME_HINTS = {
    "불편",
    "문제",
    "부족",
    "버그",
    "오류",
    "렉",
    "프레임",
    "튕김",
    "충돌",
    "지루",
    "반복",
    "과금",
    "스트레스",
    "하락",
    "느림",
    "불안정",
    "매칭 지연",
    "서버",
}

POSITIVE_THEME_HINTS = {
    "재미",
    "몰입",
    "완성도",
    "호평",
    "좋음",
    "매력",
    "만족",
    "탄탄",
    "훌륭",
    "쾌감",
    "중독",
    "손맛",
}


def is_consumer_report_payload(payload: Any) -> bool:
    """Return True when payload already matches consumer report shape."""
    if not isinstance(payload, dict):
        return False
    return REQUIRED_REPORT_KEYS.issubset(set(payload.keys()))


def build_report_ready_data(
    *,
    appid: int,
    metadata: GameMetadata,
    analysis: AnalysisResult,
    raw_reviews: list[RawReview],
    processed_reviews: list[ProcessedReview],
    pipeline_run_id: str,
) -> dict[str, Any]:
    """Build and return a purchase decision report payload."""
    metadata_payload = metadata.to_dict()
    analysis_payload = analysis.to_dict()
    processed_payload = [review.to_dict() for review in processed_reviews]
    included_count = sum(1 for review in processed_payload if review.get("included_in_analysis"))

    consensus_payload = _build_consensus_payload(
        appid=appid,
        metadata=metadata_payload,
        analysis=analysis_payload,
        processed_reviews=processed_payload,
        included_count=included_count,
    )

    report_payload = _build_report_deterministic(consensus_payload)
    if _should_use_llm_report_writer():
        writer = OpenAIReportWriter()
        llm_report = writer.generate_report(consensus_payload)
        if is_consumer_report_payload(llm_report):
            report_payload = llm_report

    return {
        "report_version": "v2-consensus-decision",
        "appid": appid,
        "pipeline_run_id": pipeline_run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_review_count": len(raw_reviews),
        "included_review_count": included_count,
        "game": {
            "name": metadata_payload.get("name"),
            "genres": list(metadata_payload.get("genres", []) or []),
            "release_stage": metadata_payload.get("release_stage"),
        },
        **report_payload,
        "disclaimer": "이 리포트는 반복적으로 관찰된 고합의 리뷰 신호를 구매 판단 관점으로 재해석한 결과입니다.",
    }


def build_consumer_report_from_snapshot(
    *,
    appid: int,
    metadata: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    processed_reviews: list[dict[str, Any]] | None = None,
    pipeline_run_id: str | None = None,
    source_review_count: int | None = None,
) -> dict[str, Any]:
    """Build deterministic report for read-only fallback serving."""
    metadata_payload = metadata or {}
    analysis_payload = analysis or {}
    processed_payload = processed_reviews or []
    included_count = sum(1 for review in processed_payload if review.get("included_in_analysis"))

    consensus_payload = _build_consensus_payload(
        appid=appid,
        metadata=metadata_payload,
        analysis=analysis_payload,
        processed_reviews=processed_payload,
        included_count=included_count,
    )
    report_payload = _build_report_deterministic(consensus_payload)

    return {
        "report_version": "v2-consensus-decision",
        "appid": appid,
        "pipeline_run_id": pipeline_run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_review_count": source_review_count,
        "included_review_count": included_count,
        "game": {
            "name": metadata_payload.get("name"),
            "genres": list(metadata_payload.get("genres", []) or []),
            "release_stage": metadata_payload.get("release_stage"),
        },
        **report_payload,
        "disclaimer": "이 리포트는 반복적으로 관찰된 고합의 리뷰 신호를 구매 판단 관점으로 재해석한 결과입니다.",
    }


def _should_use_llm_report_writer() -> bool:
    return os.getenv("USE_LLM_REPORT_WRITER", "true").strip().lower() in {"1", "true", "yes", "on"}


def _build_consensus_payload(
    *,
    appid: int,
    metadata: dict[str, Any],
    analysis: dict[str, Any],
    processed_reviews: list[dict[str, Any]],
    included_count: int,
) -> dict[str, Any]:
    issue_signals = analysis.get("issue_signals", {}) or {}
    high_min = max(12, int(round(included_count * 0.06)))
    medium_min = max(6, int(round(included_count * 0.03)))

    consensus_aspects: list[dict[str, Any]] = []
    for aspect, signal in issue_signals.items():
        mention_count = int(signal.get("mention_count", 0))
        if mention_count < medium_min:
            continue

        consensus_level = "high" if mention_count >= high_min else "medium"
        evidence_group = _collect_grouped_evidence(
            processed_reviews,
            aspect,
            list(signal.get("sample_reviews", []) or []),
        )
        negative_ratio = round(float(signal.get("negative_ratio", 0.0)), 4)
        themes = list(signal.get("themes", []) or [])

        consensus_aspects.append(
            {
                "aspect": aspect,
                "aspect_label": CATEGORY_DISPLAY.get(aspect, aspect),
                "mention_count": mention_count,
                "consensus_level": consensus_level,
                "negative_ratio": negative_ratio,
                "recent_trend": str(signal.get("recent_trend", "flat")),
                "themes": themes,
                "tone": _infer_aspect_tone(negative_ratio, themes),
                "evidence_group": evidence_group,
            }
        )

    consensus_aspects.sort(
        key=lambda item: (
            -_consensus_rank(item["consensus_level"]),
            -int(item["mention_count"]),
        )
    )

    return {
        "game_context": {
            "appid": appid,
            "name": metadata.get("name"),
            "genres": list(metadata.get("genres", []) or []),
            "analysis_window": "latest_snapshot",
            "included_review_count": included_count,
        },
        "consensus_thresholds": {
            "high_min_mentions": high_min,
            "medium_min_mentions": medium_min,
        },
        "consensus_aspects": consensus_aspects,
        "style_control": {
            "variation_seed": f"appid-{appid}-consensus-v2",
        },
    }


def _consensus_rank(level: str) -> int:
    if level == "high":
        return 2
    if level == "medium":
        return 1
    return 0


def _infer_aspect_tone(negative_ratio: float, themes: list[str]) -> str:
    score = 0
    for theme in themes:
        text = str(theme)
        if any(token in text for token in NEGATIVE_THEME_HINTS):
            score -= 1
        if any(token in text for token in POSITIVE_THEME_HINTS):
            score += 1

    if score <= -1:
        return "negative"
    if score >= 1:
        return "positive"
    if negative_ratio >= 0.58:
        return "negative"
    if negative_ratio <= 0.40:
        return "positive"
    return "mixed"


def _collect_grouped_evidence(
    processed_reviews: list[dict[str, Any]],
    aspect: str,
    fallback_snippets: list[str],
) -> dict[str, list[dict[str, Any]]]:
    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    seen: set[str] = set()

    for review in processed_reviews:
        if not review.get("included_in_analysis"):
            continue
        tags = list(review.get("category_tags", []) or [])
        if aspect not in tags:
            continue

        snippet = _truncate_text(str(review.get("review_text", "")), limit=180)
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)

        item = {"review_id": str(review.get("review_id", "")), "snippet": snippet}
        if bool(review.get("voted_up", False)):
            positive.append(item)
        else:
            negative.append(item)

        if len(positive) >= 3 and len(negative) >= 3:
            break

    if not positive and not negative:
        for index, snippet in enumerate(fallback_snippets[:3]):
            normalized = _truncate_text(str(snippet), limit=180)
            if normalized:
                negative.append(
                    {
                        "review_id": f"fallback-{aspect}-{index + 1}",
                        "snippet": normalized,
                    }
                )

    return {"positive": positive[:3], "negative": negative[:3]}


def _build_report_deterministic(consensus_payload: dict[str, Any]) -> dict[str, Any]:
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    high = [item for item in aspects if item.get("consensus_level") == "high"]
    medium = [item for item in aspects if item.get("consensus_level") == "medium"]

    selected_strengths = _select_strengths(high, medium)
    selected_risks = _select_risks(high, medium)

    recent_state = _derive_recent_state(selected_risks, high, medium)
    recommendation = _derive_recommendation(selected_risks, recent_state["status"])
    headline = _build_headline(recommendation, selected_strengths, selected_risks)
    buy_timing_summary = _build_timing_summary(recommendation, recent_state, selected_risks)

    good_for = _build_fit(
        selected_strengths,
        GOOD_FOR_PHRASES,
        fallback="핵심 시스템을 깊게 파고드는 플레이어에게 적합합니다.",
    )
    not_good_for = _build_fit(
        selected_risks,
        NOT_GOOD_FOR_PHRASES,
        fallback="기술 안정성과 완성도를 최우선으로 보는 플레이어는 주의가 필요합니다.",
    )

    return {
        "headline": headline,
        "buy_recommendation": recommendation,
        "buy_timing_summary": buy_timing_summary,
        "good_for": good_for[:4],
        "not_good_for": not_good_for[:4],
        "top_strengths": [_to_strength_item(item) for item in selected_strengths[:3]],
        "top_risks": [_to_risk_item(item) for item in selected_risks[:3]],
        "recent_state": recent_state,
        "evidence_reviews": _collect_evidence(selected_strengths, selected_risks),
    }


def _select_strengths(high: list[dict[str, Any]], medium: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool = high + medium
    candidates = [
        item
        for item in pool
        if item.get("tone") != "negative"
        and float(item.get("negative_ratio", 0.0)) <= 0.56
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (
            -_consensus_rank(item.get("consensus_level", "low")),
            0 if item.get("tone") == "positive" else 1,
            float(item.get("negative_ratio", 0.0)),
            -int(item.get("mention_count", 0)),
        ),
    )
    return ranked[:3]


def _select_risks(high: list[dict[str, Any]], medium: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool = high + medium
    candidates = [
        item
        for item in pool
        if item.get("tone") == "negative" or float(item.get("negative_ratio", 0.0)) >= 0.50
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (
            -_consensus_rank(item.get("consensus_level", "low")),
            0 if item.get("tone") == "negative" else 1,
            -float(item.get("negative_ratio", 0.0)),
            -int(item.get("mention_count", 0)),
        ),
    )
    return ranked[:3]


def _derive_recent_state(
    selected_risks: list[dict[str, Any]],
    high: list[dict[str, Any]],
    medium: list[dict[str, Any]],
) -> dict[str, str]:
    if not high and not medium:
        return {"status": "insufficient_data", "summary": "반복 신호가 충분하지 않아 최근 상태 판단을 보류합니다."}

    up = sum(1 for item in selected_risks if item.get("recent_trend") == "up")
    down = sum(1 for item in selected_risks if item.get("recent_trend") == "down")

    if selected_risks and up >= down + 1:
        return {"status": "declining", "summary": "최근 주요 리스크 언급이 증가해 체감 품질이 악화되는 흐름입니다."}
    if selected_risks and down >= up + 1:
        return {"status": "improving", "summary": "핵심 리스크 언급이 줄며 최근 체감이 개선되는 흐름입니다."}
    if selected_risks:
        return {"status": "mixed", "summary": "긍정과 리스크 신호가 동시에 관찰되어 최근 평가는 혼재 상태입니다."}
    return {"status": "stable", "summary": "고합의 신호 기준으로 최근 평가는 대체로 안정적입니다."}


def _derive_recommendation(selected_risks: list[dict[str, Any]], recent_status: str) -> str:
    severe = sum(1 for item in selected_risks if float(item.get("negative_ratio", 0.0)) >= 0.65)
    medium = sum(1 for item in selected_risks if float(item.get("negative_ratio", 0.0)) >= 0.52)

    if severe >= 2:
        return "not_recommended"
    if recent_status == "declining" and (severe >= 1 or medium >= 2):
        return "wait"
    if severe == 0 and medium <= 1 and recent_status in {"stable", "improving"}:
        return "buy_now"
    return "buy_on_sale"


def _build_headline(
    recommendation: str,
    strengths: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> str:
    strength = CATEGORY_DISPLAY.get(strengths[0]["aspect"], strengths[0]["aspect"]) if strengths else "핵심 재미"
    risk = CATEGORY_DISPLAY.get(risks[0]["aspect"], risks[0]["aspect"]) if risks else "기술 안정성"

    if recommendation == "buy_now":
        return f"{strength}에 대한 반복 호평이 뚜렷하고, 현재 구매 리스크는 제한적인 편입니다."
    if recommendation == "buy_on_sale":
        return f"{strength} 장점은 분명하지만 {risk} 이슈가 남아 있어 할인 시점 접근이 합리적입니다."
    if recommendation == "wait":
        return f"{strength} 호평은 있으나 {risk} 리스크가 누적되어, 다음 업데이트 추이를 본 뒤 구매가 안전합니다."
    return f"{risk} 관련 고합의 불만이 강해, 현재 시점 구매는 보수적으로 판단하는 편이 좋습니다."


def _build_timing_summary(
    recommendation: str,
    recent_state: dict[str, str],
    risks: list[dict[str, Any]],
) -> str:
    risk_label = CATEGORY_DISPLAY.get(risks[0]["aspect"], risks[0]["aspect"]) if risks else "핵심 리스크"
    status = recent_state.get("status", "mixed")

    if recommendation == "buy_now":
        return "최근 구간에서 주요 불만 신호가 급증하지 않아 지금 구매해도 체감 리스크가 낮습니다."
    if recommendation == "buy_on_sale":
        return f"{risk_label} 이슈가 구조적으로 남아 있어, 가격 메리트를 확보한 시점이 더 유리합니다."
    if recommendation == "wait":
        if status == "declining":
            return f"{risk_label} 불만이 최근 증가세라, 안정화 패치 이후 재확인이 안전합니다."
        return f"{risk_label} 리스크가 아직 유의미해, 단기 관망 후 구매 판단이 좋습니다."
    return f"{risk_label} 리스크가 높은 상태라, 지금은 구매보다 추세 확인이 우선입니다."


def _build_fit(
    selected_items: list[dict[str, Any]],
    phrase_map: dict[str, str],
    *,
    fallback: str,
) -> list[str]:
    result: list[str] = []
    for item in selected_items:
        aspect = str(item.get("aspect", ""))
        phrase = phrase_map.get(aspect)
        if phrase and phrase not in result:
            result.append(phrase)
    if not result:
        result.append(fallback)
    return result


def _choose_positive_theme(themes: list[str]) -> str | None:
    for theme in themes:
        text = str(theme)
        if any(token in text for token in NEGATIVE_THEME_HINTS):
            continue
        return text
    return themes[0] if themes else None


def _choose_negative_theme(themes: list[str]) -> str | None:
    for theme in themes:
        text = str(theme)
        if any(token in text for token in NEGATIVE_THEME_HINTS):
            return text
    return themes[0] if themes else None


def _to_strength_item(item: dict[str, Any]) -> dict[str, str]:
    label = CATEGORY_DISPLAY.get(item["aspect"], item["aspect"])
    mention_count = int(item.get("mention_count", 0))
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_positive_theme(themes)
    if selected_theme:
        return {
            "title": label,
            "summary": f"{selected_theme} 신호가 {mention_count}건 이상 반복되며 구매 매력으로 작동합니다.",
        }
    return {
        "title": label,
        "summary": f"{label}에 대한 긍정 신호가 반복적으로 관찰됩니다.",
    }


def _to_risk_item(item: dict[str, Any]) -> dict[str, str]:
    label = CATEGORY_DISPLAY.get(item["aspect"], item["aspect"])
    mention_count = int(item.get("mention_count", 0))
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_negative_theme(themes)
    if selected_theme:
        return {
            "title": label,
            "summary": f"{selected_theme} 이슈가 {mention_count}건 이상 반복돼 구매 리스크로 작용합니다.",
        }
    return {
        "title": label,
        "summary": f"{label} 관련 불만이 누적되어 주의가 필요합니다.",
    }


def _collect_evidence(
    strengths: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []

    for item in risks[:2]:
        evidence.extend(_collect_evidence_for_item(item, "negative"))
    for item in strengths[:2]:
        evidence.extend(_collect_evidence_for_item(item, "positive"))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in evidence:
        snippet = item.get("snippet", "")
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)
        deduped.append(item)
        if len(deduped) >= 8:
            break
    return deduped


def _collect_evidence_for_item(item: dict[str, Any], stance: str) -> list[dict[str, Any]]:
    aspect = str(item.get("aspect", ""))
    aspect_label = CATEGORY_DISPLAY.get(aspect, aspect)
    grouped = item.get("evidence_group", {}) or {}

    snippets = list(grouped.get(stance, []) or [])
    if not snippets:
        snippets = list(grouped.get("negative", []) or []) + list(grouped.get("positive", []) or [])

    result: list[dict[str, Any]] = []
    for snippet in snippets[:2]:
        result.append(
            {
                "review_id": str(snippet.get("review_id", "")),
                "aspect": aspect,
                "aspect_label": aspect_label,
                "stance": stance if stance in {"positive", "negative"} else "mixed",
                "snippet": _truncate_text(str(snippet.get("snippet", "")), limit=200),
            }
        )
    return result


def _truncate_text(text: str, limit: int = 220) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"

