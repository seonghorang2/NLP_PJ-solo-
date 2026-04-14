"""Consumer-facing purchase decision report builders."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from models.schemas import AnalysisResult, GameMetadata, ProcessedReview, RawReview
from services.evidence_snippet_llm import OpenAIEvidenceSnippetCompressor
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
    "content_depth": "장시간 성장 루프를 선호하는 플레이어",
    "difficulty": "숙련형 플레이를 선호하는 플레이어",
}

NOT_GOOD_FOR_PHRASES = {
    "performance": "프레임 저하나 끊김에 민감한 플레이어",
    "bugs": "버그/충돌 허용 범위가 낮은 플레이어",
    "difficulty": "초반 진입장벽이 낮은 게임을 원하는 플레이어",
    "difficulty_onboarding": "튜토리얼 완성도를 중요하게 보는 플레이어",
    "save_progression": "진행 데이터 안정성을 최우선으로 보는 플레이어",
    "mod_support": "모드 활용이 필수인 플레이어",
    "matchmaking": "멀티 매칭 안정성을 최우선으로 보는 플레이어",
    "multiplayer": "팀플레이 품질에 민감한 플레이어",
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
    "매칭",
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
    if not REQUIRED_REPORT_KEYS.issubset(set(payload.keys())):
        return False
    if not _is_evidence_block_list(payload.get("evidence_reviews")):
        return False
    evidence_sections = payload.get("evidence_sections")
    if evidence_sections is None:
        return True
    return _is_evidence_sections_map(evidence_sections)


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

    # Offline stage only: compress all evidence snippets with LLM (fallback to rules).
    report_payload = _compress_evidence_reviews(report_payload, use_llm=True)
    report_payload = _attach_evidence_sections(report_payload)

    return {
        "report_version": "v3-insight-evidence",
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

    # Read-only path: keep deterministic compression only (no online LLM call).
    report_payload = _compress_evidence_reviews(report_payload, use_llm=False)
    report_payload = _attach_evidence_sections(report_payload)

    return {
        "report_version": "v3-insight-evidence",
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


def _should_use_llm_evidence_compression() -> bool:
    return os.getenv("USE_LLM_EVIDENCE_COMPRESSION", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
        negative_ratio = round(float(signal.get("negative_ratio", 0.0)), 4)
        themes = list(signal.get("themes", []) or [])
        evidence_group = _collect_grouped_evidence(
            processed_reviews=processed_reviews,
            aspect=aspect,
            fallback_snippets=list(signal.get("sample_reviews", []) or []),
        )

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
        key=lambda item: (-_consensus_rank(item["consensus_level"]), -int(item["mention_count"]))
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
    *,
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

        snippet = _prepare_evidence_source_text(str(review.get("review_text", "")), limit=1200)
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)

        item = {"review_id": str(review.get("review_id", "")), "snippet": snippet}
        if bool(review.get("voted_up", False)):
            positive.append(item)
        else:
            negative.append(item)

        if len(positive) >= 4 and len(negative) >= 4:
            break

    if not positive and not negative:
        for index, snippet in enumerate(fallback_snippets[:3]):
            normalized = _prepare_evidence_source_text(str(snippet), limit=1200)
            if normalized:
                negative.append(
                    {
                        "review_id": f"fallback-{aspect}-{index + 1}",
                        "snippet": normalized,
                    }
                )

    return {"positive": positive[:4], "negative": negative[:4]}


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
    evidence_blocks = _build_evidence_blocks(consensus_payload)

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
        "evidence_reviews": evidence_blocks,
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


def _build_evidence_blocks(consensus_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build insight+evidence blocks from high-consensus repeated opinions."""
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    high_min = int(
        (consensus_payload.get("consensus_thresholds", {}) or {}).get("high_min_mentions", 12)
    )
    high_items = [item for item in aspects if item.get("consensus_level") == "high"]
    if not high_items:
        return []

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in high_items:
        stance = _block_stance(item)
        if stance not in {"positive", "negative"}:
            continue

        theme = _pick_block_theme(item, stance) or str(item.get("aspect_label", "핵심 의견"))
        key = (stance, theme)
        bucket = grouped.setdefault(
            key,
            {
                "stance": stance,
                "theme": theme,
                "mention_count": 0,
                "aspect_labels": [],
                "snippets": [],
            },
        )

        bucket["mention_count"] += int(item.get("mention_count", 0))
        aspect_label = str(item.get("aspect_label", ""))
        if aspect_label and aspect_label not in bucket["aspect_labels"]:
            bucket["aspect_labels"].append(aspect_label)

        evidence_group = item.get("evidence_group", {}) or {}
        stance_snippets = list(evidence_group.get(stance, []) or [])
        for snippet in stance_snippets[:3]:
            text = _prepare_evidence_source_text(str(snippet.get("snippet", "")), limit=1200)
            if text and text not in bucket["snippets"]:
                bucket["snippets"].append(text)

    blocks: list[dict[str, Any]] = []
    for bucket in sorted(grouped.values(), key=lambda b: (-int(b["mention_count"]), b["theme"])):
        if int(bucket["mention_count"]) < high_min:
            continue
        if len(bucket["snippets"]) < 2:
            continue

        title = _build_block_title(bucket["theme"], bucket["aspect_labels"])
        explanation = _build_block_explanation(
            stance=bucket["stance"],
            theme=bucket["theme"],
            mention_count=int(bucket["mention_count"]),
            aspect_labels=bucket["aspect_labels"],
        )
        blocks.append(
            {
                "title": title,
                "explanation": explanation,
                "stance": bucket["stance"],
                "consensus_level": "high",
                "mention_count": int(bucket["mention_count"]),
                "evidence_snippets": bucket["snippets"][:3],
            }
        )
        if len(blocks) >= 4:
            break
    return blocks


def _block_stance(item: dict[str, Any]) -> str:
    tone = str(item.get("tone", "mixed"))
    negative_ratio = float(item.get("negative_ratio", 0.0))
    if tone == "negative" or negative_ratio >= 0.55:
        return "negative"
    if tone == "positive" or negative_ratio <= 0.40:
        return "positive"
    return "mixed"


def _pick_block_theme(item: dict[str, Any], stance: str) -> str | None:
    themes = [str(theme) for theme in list(item.get("themes", []) or []) if str(theme).strip()]
    if not themes:
        return None
    if stance == "negative":
        return _choose_negative_theme(themes)
    return _choose_positive_theme(themes)


def _build_block_title(theme: str, aspect_labels: list[str]) -> str:
    base = aspect_labels[0] if aspect_labels else "핵심 의견"
    return f"[{base}] {theme}"


def _build_block_explanation(
    *,
    stance: str,
    theme: str,
    mention_count: int,
    aspect_labels: list[str],
) -> str:
    aspect_text = ", ".join(aspect_labels[:2]) if aspect_labels else "핵심 경험"
    if stance == "negative":
        return (
            f"{aspect_text} 영역에서 '{theme}' 불만이 반복적으로 관찰됩니다. "
            f"동일한 문제 제기가 {mention_count}건 이상 누적되어 구매 리스크로 해석됩니다."
        )
    return (
        f"{aspect_text} 영역에서 '{theme}' 호평이 반복됩니다. "
        f"유사한 긍정 신호가 {mention_count}건 이상 확인되어 만족 포인트로 볼 수 있습니다."
    )


def _compress_evidence_reviews(
    report_payload: dict[str, Any],
    *,
    use_llm: bool,
) -> dict[str, Any]:
    """Compress evidence snippets into readable 1~4 sentence snippets."""
    evidence_blocks = report_payload.get("evidence_reviews")
    if not isinstance(evidence_blocks, list):
        return report_payload

    compressor = (
        OpenAIEvidenceSnippetCompressor()
        if use_llm and _should_use_llm_evidence_compression()
        else None
    )
    llm_enabled = bool(compressor and compressor.available)

    compressed_blocks: list[dict[str, Any]] = []
    for block in evidence_blocks:
        if not isinstance(block, dict):
            continue
        snippets = block.get("evidence_snippets")
        if not isinstance(snippets, list):
            continue

        rewritten: list[str] = []
        seen: set[str] = set()
        for raw in snippets:
            raw_text = str(raw or "").strip()
            if not raw_text:
                continue

            compressed: str | None = None
            if llm_enabled and compressor is not None:
                compressed = compressor.compress(
                    raw_text=raw_text,
                    stance=str(block.get("stance", "mixed")),
                    context_title=str(block.get("title", "핵심 의견")),
                    timeout_seconds=15,
                    retry_limit=1,
                )
            if not compressed:
                compressed = _fallback_compress_snippet(raw_text)

            normalized = _normalize_compressed_snippet(compressed)
            if _looks_cutoff(normalized):
                normalized = _normalize_compressed_snippet(_fallback_compress_snippet(raw_text))
            if not normalized or _looks_cutoff(normalized):
                continue

            if normalized not in seen:
                seen.add(normalized)
                rewritten.append(normalized)
            if len(rewritten) >= 3:
                break

        # Keep only blocks with enough readable evidence.
        if len(rewritten) < 2:
            continue

        next_block = dict(block)
        next_block["evidence_snippets"] = rewritten[:3]
        compressed_blocks.append(next_block)

    next_payload = dict(report_payload)
    next_payload["evidence_reviews"] = compressed_blocks
    return next_payload


def _attach_evidence_sections(report_payload: dict[str, Any]) -> dict[str, Any]:
    """Attach strictly separated positive/negative evidence sections."""
    blocks = report_payload.get("evidence_reviews")
    if not isinstance(blocks, list):
        next_payload = dict(report_payload)
        next_payload["evidence_sections"] = {"loved": [], "complained": []}
        return next_payload

    loved = [block for block in blocks if isinstance(block, dict) and block.get("stance") == "positive"]
    complained = [
        block for block in blocks if isinstance(block, dict) and block.get("stance") == "negative"
    ]
    next_payload = dict(report_payload)
    next_payload["evidence_sections"] = {
        "loved": loved,
        "complained": complained,
    }
    return next_payload


def _fallback_compress_snippet(raw_text: str) -> str:
    """Deterministic fallback: keep 1~4 full sentences."""
    source = _prepare_evidence_source_text(raw_text, limit=700)
    if not source:
        return ""
    sentences = _split_sentences(source)
    if not sentences:
        return source

    selected = sentences[:4]
    result = " ".join(selected).strip()
    if len(result) > 360:
        result = _prepare_evidence_source_text(result, limit=360)
    return result


def _prepare_evidence_source_text(text: str, limit: int = 1200) -> str:
    """Keep source text readable and avoid mid-sentence truncation."""
    compact = " ".join((text or "").split())
    if not compact:
        return ""
    if len(compact) <= limit:
        return compact

    sentences = _split_sentences(compact)
    if not sentences:
        return compact[:limit].rstrip()

    selected: list[str] = []
    total = 0
    for sentence in sentences:
        extra = len(sentence) + (1 if selected else 0)
        if total + extra > limit:
            break
        selected.append(sentence)
        total += extra

    if selected:
        return " ".join(selected)
    return sentences[0][:limit].rstrip()


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _normalize_compressed_snippet(text: str) -> str:
    normalized = " ".join((text or "").split())
    if not normalized:
        return ""
    normalized = normalized.replace("…", ".")
    normalized = normalized.replace("...", ".")
    normalized = re.sub(r"\s*\.\s*\.\s*", ". ", normalized)
    return " ".join(normalized.split()).strip()


def _looks_cutoff(text: str) -> bool:
    target = (text or "").strip()
    if not target:
        return True
    if target.endswith("…") or target.endswith("..."):
        return True
    if target.endswith(",") or target.endswith("，"):
        return True
    return False


def _is_evidence_block_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("title"), str):
            return False
        if not isinstance(item.get("explanation"), str):
            return False
        if item.get("stance") not in {"positive", "negative"}:
            return False
        if item.get("consensus_level") not in {"high", "medium"}:
            return False
        if not isinstance(item.get("mention_count"), int):
            return False
        snippets = item.get("evidence_snippets")
        if not isinstance(snippets, list):
            return False
        if len(snippets) < 2 or len(snippets) > 3:
            return False
        if any(not isinstance(snippet, str) for snippet in snippets):
            return False
    return True


def _is_evidence_sections_map(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    loved = value.get("loved")
    complained = value.get("complained")
    if not _is_evidence_block_list(loved):
        return False
    if not _is_evidence_block_list(complained):
        return False
    if any(item.get("stance") != "positive" for item in loved):
        return False
    if any(item.get("stance") != "negative" for item in complained):
        return False
    return True
