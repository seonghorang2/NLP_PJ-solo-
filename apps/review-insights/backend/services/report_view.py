"""Consumer-facing purchase decision report builders."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from models.schemas import AnalysisResult, GameMetadata, ProcessedReview, RawReview
from services.evidence_judge_llm import OpenAIEvidenceJudge
from services.korean_report_proofreader import KoreanReportProofreader
from services.report_writer_llm import OpenAIReportWriter, validate_structured_report_payload

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
    "monetization": "과금/가격",
    "gameplay": "전투/핵심 플레이",
    "story": "스토리/몰입",
    "customization": "커스터마이징",
    "building_ux": "건축/배치 UX",
    "save_progression": "저장/진행 안정성",
    "mod_support": "모드 지원/호환성",
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

EVIDENCE_POSITIVE_HINTS = {
    "재밌",
    "재미",
    "좋",
    "만족",
    "몰입",
    "훌륭",
    "손맛",
    "추천",
}

EVIDENCE_NEGATIVE_HINTS = {
    "불편",
    "문제",
    "버그",
    "오류",
    "렉",
    "프레임",
    "끊김",
    "튕김",
    "지루",
    "답답",
    "하락",
    "스트레스",
}

ASPECT_EVIDENCE_HINTS = {
    "gameplay": ("전투", "타격", "손맛", "보스", "무기", "빌드", "스킬", "탐험"),
    "performance": ("프레임", "렉", "끊김", "최적화", "버벅", "튕김"),
    "bugs": ("버그", "오류", "에러", "멈춤", "충돌"),
    "monetization": ("가격", "과금", "현질", "유료", "결제", "확장팩"),
    "story": ("스토리", "서사", "몰입", "캐릭터", "연출"),
    "difficulty": ("난이도", "어려", "초보", "튜토리얼", "입문"),
    "difficulty_onboarding": ("튜토리얼", "설명", "가이드", "입문", "초반"),
    "graphics": ("그래픽", "비주얼", "연출", "아트", "풍경"),
    "sound": ("사운드", "음악", "bgm", "효과음", "음향"),
    "controls": ("조작", "ui", "키설정", "인터페이스", "입력"),
    "content_depth": ("볼륨", "콘텐츠", "반복", "파밍", "엔드게임"),
    "customization": ("커스터마이징", "외형", "빌드", "의상", "꾸미"),
    "save_progression": ("저장", "세이브", "진행", "롤백", "손실"),
    "matchmaking": ("매칭", "큐", "서버", "대기시간", "핑"),
    "multiplayer": ("멀티", "협동", "팀플", "파티", "네트워크"),
    "balance": ("밸런스", "메타", "너프", "버프", "불공정"),
    "localization": ("번역", "로컬", "자막", "텍스트", "오역"),
}

GOOD_FOR_SCENARIOS = {
    "gameplay": "긴 보스전에서 패턴을 익히고 반복 트라이를 즐기는 플레이어",
    "story": "전투 속도보다 서사와 분위기 몰입을 우선하는 플레이어",
    "graphics": "시각 연출과 월드 분위기를 천천히 감상하며 플레이하는 플레이어",
    "customization": "캐릭터 외형과 빌드를 오래 만지며 플레이하는 플레이어",
    "content_depth": "하루에 오래 붙잡고 성장 루프를 깊게 파는 플레이어",
    "difficulty": "난관을 반복 시도하며 실력을 올리는 과정 자체를 즐기는 플레이어",
}

NOT_GOOD_FOR_SCENARIOS = {
    "performance": "짧은 플레이 시간에도 프레임 안정성이 꼭 필요한 환경에서 즐기려는 플레이어",
    "bugs": "진행 중 오류나 예기치 않은 끊김을 거의 허용하지 않는 플레이어",
    "difficulty": "초반부터 편하게 진행되는 난이도를 기대하는 플레이어",
    "difficulty_onboarding": "튜토리얼 안내가 충분해야 시작할 수 있는 플레이어",
    "save_progression": "플레이 기록 보존을 최우선으로 보는 플레이어",
    "matchmaking": "멀티 매칭 품질이 낮으면 즉시 이탈하는 플레이어",
    "multiplayer": "팀플레이 품질과 소통 스트레스를 크게 받는 플레이어",
    "balance": "메타 변동에 민감해 작은 밸런스 변화도 피로하게 느끼는 플레이어",
    "monetization": "가격 대비 체감 만족을 매우 엄격하게 따지는 플레이어",
}

PAID_RECOMMENDATIONS = {"buy_now", "buy_on_sale", "wait", "not_recommended"}
FREE_RECOMMENDATIONS = {"free_play_recommended", "play_now", "try_lightly", "wait", "not_recommended"}
ALL_RECOMMENDATIONS = PAID_RECOMMENDATIONS | FREE_RECOMMENDATIONS


def is_consumer_report_payload(payload: Any) -> bool:
    """Return True when payload matches the multi-stage report contract."""
    return validate_structured_report_payload(payload)


def build_report_ready_data(
    *,
    appid: int,
    metadata: GameMetadata,
    analysis: AnalysisResult,
    raw_reviews: list[RawReview],
    processed_reviews: list[ProcessedReview],
    report_materials: list[dict[str, Any]] | None = None,
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
        report_materials=report_materials or [],
        included_count=included_count,
    )

    structured_report = _build_structured_report_bundle(
        consensus_payload=consensus_payload,
        enable_llm_sections=True,
        enable_llm_evidence_compression=True,
    )

    payload = {
        "report_version": "v4-planned-sections",
        "appid": appid,
        "pipeline_run_id": pipeline_run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_review_count": len(raw_reviews),
        "included_review_count": included_count,
        "game": {
            "name": metadata_payload.get("name"),
            "genres": list(metadata_payload.get("genres", []) or []),
            "price_model": metadata_payload.get("price_model"),
            "is_free": metadata_payload.get("is_free"),
            "release_stage": metadata_payload.get("release_stage"),
        },
        **structured_report,
        "disclaimer": "이 리포트는 반복적으로 관찰된 고합의 리뷰 신호를 구매 판단 관점으로 재해석한 결과입니다.",
    }
    return _attach_legacy_flat_fields(payload)


def build_consumer_report_from_snapshot(
    *,
    appid: int,
    metadata: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    processed_reviews: list[dict[str, Any]] | None = None,
    report_materials: list[dict[str, Any]] | None = None,
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
        report_materials=report_materials or [],
        included_count=included_count,
    )
    structured_report = _build_structured_report_bundle(
        consensus_payload=consensus_payload,
        enable_llm_sections=False,
        enable_llm_evidence_compression=False,
    )

    payload = {
        "report_version": "v4-planned-sections",
        "appid": appid,
        "pipeline_run_id": pipeline_run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_review_count": source_review_count,
        "included_review_count": included_count,
        "game": {
            "name": metadata_payload.get("name"),
            "genres": list(metadata_payload.get("genres", []) or []),
            "price_model": metadata_payload.get("price_model"),
            "is_free": metadata_payload.get("is_free"),
            "release_stage": metadata_payload.get("release_stage"),
        },
        **structured_report,
        "disclaimer": "이 리포트는 반복적으로 관찰된 고합의 리뷰 신호를 구매 판단 관점으로 재해석한 결과입니다.",
    }
    return _attach_legacy_flat_fields(payload)


def _should_use_llm_report_writer() -> bool:
    return os.getenv("USE_LLM_REPORT_WRITER", "true").strip().lower() in {"1", "true", "yes", "on"}


def _should_use_llm_evidence_judge() -> bool:
    return os.getenv("USE_LLM_EVIDENCE_JUDGE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_structured_report_bundle(
    *,
    consensus_payload: dict[str, Any],
    enable_llm_sections: bool,
    enable_llm_evidence_compression: bool,
) -> dict[str, Any]:
    """Run multi-stage report generation:
    1) report_plan
    2) section-wise report_display
    3) evidence grouping + snippet compression
    """
    seed_display = _build_report_deterministic(consensus_payload)
    seed_plan = _build_report_plan_deterministic(consensus_payload, seed_display)
    seed_evidence_sections = _build_evidence_sections_from_blocks(
        list(seed_display.get("evidence_reviews", []) or [])
    )

    report_plan = seed_plan
    report_display = {k: v for k, v in seed_display.items() if k != "evidence_reviews"}
    writer = OpenAIReportWriter()

    if enable_llm_sections and _should_use_llm_report_writer() and writer.available:
        llm_plan = writer.generate_report_plan(
            consensus_payload=consensus_payload,
            seed_plan=seed_plan,
        )
        if isinstance(llm_plan, dict):
            report_plan = llm_plan

        llm_display = writer.generate_report_display(
            consensus_payload=consensus_payload,
            report_plan=report_plan,
            seed_display=report_display,
        )
        if isinstance(llm_display, dict):
            report_display = llm_display

    evidence_sections = _compress_evidence_sections(
        seed_evidence_sections,
        use_llm=enable_llm_evidence_compression,
    )
    evidence_sections = _truncate_evidence_sections_by_plan(evidence_sections, report_plan)

    payload = {
        "report_plan": report_plan,
        "report_display": report_display,
        "evidence_sections": evidence_sections,
    }
    if validate_structured_report_payload(payload):
        finalized = _apply_price_aware_recommendation_to_payload(
            payload=payload,
            consensus_payload=consensus_payload,
        )
        finalized = _apply_final_language_polish(
            payload=finalized,
            allow_llm=bool(enable_llm_sections),
            is_free_game=_is_free_game(consensus_payload),
        )
        if validate_structured_report_payload(finalized):
            return finalized

    # Hard fallback to deterministic multi-stage result.
    fallback = {
        "report_plan": seed_plan,
        "report_display": {k: v for k, v in seed_display.items() if k != "evidence_reviews"},
        "evidence_sections": _truncate_evidence_sections_by_plan(
            _compress_evidence_sections(seed_evidence_sections, use_llm=False),
            seed_plan,
        ),
    }
    fallback = _apply_price_aware_recommendation_to_payload(
        payload=fallback,
        consensus_payload=consensus_payload,
    )
    fallback = _apply_final_language_polish(
        payload=fallback,
        allow_llm=False,
        is_free_game=_is_free_game(consensus_payload),
    )
    return fallback


def _build_report_plan_deterministic(
    consensus_payload: dict[str, Any],
    seed_display: dict[str, Any],
) -> dict[str, Any]:
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    strengths = [item for item in aspects if _block_stance(item) == "positive"][:3]
    risks = [item for item in aspects if _block_stance(item) == "negative"][:3]
    recommendation = str(seed_display.get("buy_recommendation", "buy_on_sale"))

    strength_reasons = [
        {
            "reason_id": f"str_{index + 1}",
            "aspect": str(item.get("aspect", "")),
            "theme": _pick_block_theme(item, "positive")
            or str(item.get("aspect_label", "핵심 강점")),
        }
        for index, item in enumerate(strengths)
    ]
    risk_reasons = [
        {
            "reason_id": f"risk_{index + 1}",
            "aspect": str(item.get("aspect", "")),
            "theme": _pick_block_theme(item, "negative")
            or str(item.get("aspect_label", "핵심 리스크")),
        }
        for index, item in enumerate(risks)
    ]
    primary_reason_ids = [item["reason_id"] for item in (risk_reasons + strength_reasons)[:2]]

    return {
        "decision_anchor": {
            "buy_recommendation": recommendation,
            "primary_reason_ids": primary_reason_ids,
            "rationale_short": str(seed_display.get("buy_timing_summary", "")),
        },
        "section_blueprint": {
            "strength_block_count": 3,
            "risk_block_count": 3,
            "evidence_per_block": 3,
        },
        "theme_priorities": {
            "strengths": strength_reasons,
            "risks": risk_reasons,
        },
    }


def _is_llm_report_proofread_enabled() -> bool:
    return os.getenv("USE_LLM_REPORT_PROOFREAD", "true").strip().lower() in {"1", "true", "yes", "on"}


def _is_free_game(consensus_payload: dict[str, Any]) -> bool:
    game_context = consensus_payload.get("game_context", {}) if isinstance(consensus_payload, dict) else {}
    if bool(game_context.get("is_free")):
        return True
    return str(game_context.get("price_model", "")) == "free_to_play"


def _to_price_aware_recommendation(value: str, *, is_free_game: bool) -> str:
    recommendation = str(value or "").strip()
    if not recommendation:
        recommendation = "buy_on_sale"
    if recommendation not in ALL_RECOMMENDATIONS:
        recommendation = "buy_on_sale"

    if not is_free_game:
        if recommendation in FREE_RECOMMENDATIONS - {"wait", "not_recommended"}:
            return "buy_now"
        return recommendation if recommendation in PAID_RECOMMENDATIONS else "buy_on_sale"

    free_mapping = {
        "buy_now": "free_play_recommended",
        "buy_on_sale": "try_lightly",
        "free_play_recommended": "free_play_recommended",
        "play_now": "play_now",
        "try_lightly": "try_lightly",
        "wait": "wait",
        "not_recommended": "not_recommended",
    }
    return free_mapping.get(recommendation, "try_lightly")


def _apply_price_aware_recommendation_to_payload(
    *,
    payload: dict[str, Any],
    consensus_payload: dict[str, Any],
) -> dict[str, Any]:
    is_free_game = _is_free_game(consensus_payload)
    report_plan = dict(payload.get("report_plan", {}) or {})
    report_display = dict(payload.get("report_display", {}) or {})

    decision_anchor = dict(report_plan.get("decision_anchor", {}) or {})
    plan_rec = _to_price_aware_recommendation(
        str(decision_anchor.get("buy_recommendation", report_display.get("buy_recommendation", "buy_on_sale"))),
        is_free_game=is_free_game,
    )
    decision_anchor["buy_recommendation"] = plan_rec
    report_plan["decision_anchor"] = decision_anchor

    display_rec = _to_price_aware_recommendation(
        str(report_display.get("buy_recommendation", plan_rec)),
        is_free_game=is_free_game,
    )
    report_display["buy_recommendation"] = display_rec

    if is_free_game:
        report_display["headline"] = _rewrite_free_game_text(str(report_display.get("headline", "")))
        report_display["buy_timing_summary"] = _rewrite_free_game_text(
            str(report_display.get("buy_timing_summary", ""))
        )

    merged = dict(payload)
    merged["report_plan"] = report_plan
    merged["report_display"] = report_display
    return merged


def _rewrite_free_game_text(text: str) -> str:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return normalized

    replacements = (
        ("할인 구매", "무료 플레이"),
        ("할인 시점", "시작 시점"),
        ("할인", "무료"),
        ("지금 구매", "지금 플레이"),
        ("구매", "플레이"),
        ("사는 것이", "시작하는 것이"),
        ("사도", "플레이해도"),
        ("사는 편이", "시작하는 편이"),
    )
    result = normalized
    for before, after in replacements:
        result = result.replace(before, after)
    return result


def _apply_final_language_polish(
    *,
    payload: dict[str, Any],
    allow_llm: bool,
    is_free_game: bool,
) -> dict[str, Any]:
    report_plan = dict(payload.get("report_plan", {}) or {})
    report_display = dict(payload.get("report_display", {}) or {})
    evidence_sections = payload.get("evidence_sections", {}) or {}

    proofreader = KoreanReportProofreader()
    llm_enabled = bool(allow_llm and _is_llm_report_proofread_enabled() and proofreader.available)

    def _fix(text: str) -> str:
        source = _rewrite_free_game_text(text) if is_free_game else str(text or "")
        return proofreader.proofread_text(source, allow_llm=llm_enabled)

    decision_anchor = dict(report_plan.get("decision_anchor", {}) or {})
    if isinstance(decision_anchor.get("rationale_short"), str):
        decision_anchor["rationale_short"] = _fix(str(decision_anchor.get("rationale_short", "")))
    report_plan["decision_anchor"] = decision_anchor

    if isinstance(report_display.get("headline"), str):
        report_display["headline"] = _fix(str(report_display.get("headline", "")))
    if isinstance(report_display.get("buy_timing_summary"), str):
        report_display["buy_timing_summary"] = _fix(str(report_display.get("buy_timing_summary", "")))

    good_for = []
    for item in list(report_display.get("good_for", []) or []):
        good_for.append(_fix(str(item)))
    report_display["good_for"] = good_for

    not_good_for = []
    for item in list(report_display.get("not_good_for", []) or []):
        not_good_for.append(_fix(str(item)))
    report_display["not_good_for"] = not_good_for

    top_strengths = []
    for item in list(report_display.get("top_strengths", []) or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        if isinstance(next_item.get("title"), str):
            next_item["title"] = _fix(str(next_item.get("title", "")))
        if isinstance(next_item.get("summary"), str):
            next_item["summary"] = _fix(str(next_item.get("summary", "")))
        top_strengths.append(next_item)
    report_display["top_strengths"] = top_strengths

    top_risks = []
    for item in list(report_display.get("top_risks", []) or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        if isinstance(next_item.get("title"), str):
            next_item["title"] = _fix(str(next_item.get("title", "")))
        if isinstance(next_item.get("summary"), str):
            next_item["summary"] = _fix(str(next_item.get("summary", "")))
        top_risks.append(next_item)
    report_display["top_risks"] = top_risks

    recent_state = dict(report_display.get("recent_state", {}) or {})
    if isinstance(recent_state.get("summary"), str):
        recent_state["summary"] = _fix(str(recent_state.get("summary", "")))
    report_display["recent_state"] = recent_state

    def _fix_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fixed: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            next_block = dict(block)
            if isinstance(next_block.get("title"), str):
                next_block["title"] = _fix(str(next_block.get("title", "")))
            if isinstance(next_block.get("why_it_matters"), str):
                next_block["why_it_matters"] = _fix(str(next_block.get("why_it_matters", "")))
            if isinstance(next_block.get("explanation"), str):
                next_block["explanation"] = _fix(str(next_block.get("explanation", "")))
            snippets: list[str] = []
            for snippet in list(next_block.get("evidence_snippets", []) or []):
                snippets.append(_fix(str(snippet)))
            next_block["evidence_snippets"] = snippets
            fixed.append(next_block)
        return fixed

    next_sections = {
        "strengths": _fix_blocks(list(evidence_sections.get("strengths", []) or [])),
        "risks": _fix_blocks(list(evidence_sections.get("risks", []) or [])),
    }

    merged = dict(payload)
    merged["report_plan"] = report_plan
    merged["report_display"] = report_display
    merged["evidence_sections"] = next_sections
    return merged


def _build_evidence_sections_from_blocks(blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    strengths: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    strength_index = 1
    risk_index = 1

    for block in blocks:
        if not isinstance(block, dict):
            continue
        stance = str(block.get("stance", ""))
        snippets = [str(item) for item in list(block.get("evidence_snippets", []) or []) if str(item)]
        candidate_snippets = [
            str(item)
            for item in list(block.get("evidence_candidate_snippets", []) or [])
            if str(item)
        ]
        if len(snippets) < 2:
            continue
        if stance == "positive":
            strengths.append(
                {
                    "block_id": f"str_{strength_index}",
                    "title": str(block.get("title", "")),
                    "theme": str(block.get("theme", "")),
                    "why_it_matters": str(block.get("why_it_matters") or block.get("explanation", "")),
                    "explanation": str(block.get("explanation", "")),
                    "aspect_keys": list(block.get("aspect_keys", []) or []),
                    "stance": "positive",
                    "consensus_level": str(block.get("consensus_level", "high")),
                    "mention_count": int(block.get("mention_count", 0)),
                    "evidence_quality_level": str(block.get("evidence_quality_level", "strict")),
                    "evidence_candidate_snippets": candidate_snippets[:8],
                    "evidence_snippets": snippets[:3],
                }
            )
            strength_index += 1
        elif stance == "negative":
            risks.append(
                {
                    "block_id": f"risk_{risk_index}",
                    "title": str(block.get("title", "")),
                    "theme": str(block.get("theme", "")),
                    "why_it_matters": str(block.get("why_it_matters") or block.get("explanation", "")),
                    "explanation": str(block.get("explanation", "")),
                    "aspect_keys": list(block.get("aspect_keys", []) or []),
                    "stance": "negative",
                    "consensus_level": str(block.get("consensus_level", "high")),
                    "mention_count": int(block.get("mention_count", 0)),
                    "evidence_quality_level": str(block.get("evidence_quality_level", "strict")),
                    "evidence_candidate_snippets": candidate_snippets[:8],
                    "evidence_snippets": snippets[:3],
                }
            )
            risk_index += 1

    return {
        "strengths": strengths[:3],
        "risks": risks[:3],
    }


def _truncate_evidence_sections_by_plan(
    evidence_sections: dict[str, list[dict[str, Any]]],
    report_plan: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    blueprint = report_plan.get("section_blueprint", {}) if isinstance(report_plan, dict) else {}
    strength_count = int(blueprint.get("strength_block_count", 3))
    risk_count = int(blueprint.get("risk_block_count", 3))
    evidence_per_block = int(blueprint.get("evidence_per_block", 3))
    if evidence_per_block < 2:
        evidence_per_block = 2
    if evidence_per_block > 3:
        evidence_per_block = 3

    clipped_strengths = []
    for block in list(evidence_sections.get("strengths", []) or [])[: max(strength_count, 0)]:
        next_block = dict(block)
        next_block["evidence_snippets"] = list(block.get("evidence_snippets", []) or [])[: max(
            evidence_per_block, 0
        )]
        clipped_strengths.append(next_block)

    clipped_risks = []
    for block in list(evidence_sections.get("risks", []) or [])[: max(risk_count, 0)]:
        next_block = dict(block)
        next_block["evidence_snippets"] = list(block.get("evidence_snippets", []) or [])[: max(
            evidence_per_block, 0
        )]
        clipped_risks.append(next_block)

    return {
        "strengths": clipped_strengths,
        "risks": clipped_risks,
    }


def _attach_legacy_flat_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep backward-compatible top-level fields for existing UI routes."""
    report_display = payload.get("report_display", {}) if isinstance(payload, dict) else {}
    evidence_sections = payload.get("evidence_sections", {}) if isinstance(payload, dict) else {}

    evidence_reviews: list[dict[str, Any]] = []
    for block in list(evidence_sections.get("strengths", []) or []):
        merged = dict(block)
        merged["stance"] = "positive"
        evidence_reviews.append(merged)
    for block in list(evidence_sections.get("risks", []) or []):
        merged = dict(block)
        merged["stance"] = "negative"
        evidence_reviews.append(merged)

    merged_payload = dict(payload)
    merged_payload.update(
        {
            "headline": report_display.get("headline"),
            "buy_recommendation": report_display.get("buy_recommendation"),
            "buy_timing_summary": report_display.get("buy_timing_summary"),
            "good_for": report_display.get("good_for"),
            "not_good_for": report_display.get("not_good_for"),
            "top_strengths": report_display.get("top_strengths"),
            "top_risks": report_display.get("top_risks"),
            "recent_state": report_display.get("recent_state"),
            "evidence_reviews": evidence_reviews,
        }
    )
    return merged_payload


def _build_consensus_payload(
    *,
    appid: int,
    metadata: dict[str, Any],
    analysis: dict[str, Any],
    processed_reviews: list[dict[str, Any]],
    report_materials: list[dict[str, Any]],
    included_count: int,
) -> dict[str, Any]:
    issue_signals = analysis.get("issue_signals", {}) or {}
    high_min = max(12, int(round(included_count * 0.06)))
    medium_min = max(6, int(round(included_count * 0.03)))
    refined_material_map = _build_refined_material_map(report_materials)

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
            refined_material_map=refined_material_map,
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
            "price_model": metadata.get("price_model"),
            "is_free": metadata.get("is_free"),
            "analysis_window": "latest_snapshot",
            "included_review_count": included_count,
        },
        "consensus_thresholds": {
            "high_min_mentions": high_min,
            "medium_min_mentions": medium_min,
        },
        "report_materials": list(report_materials or [])[:50],
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
    refined_material_map: dict[str, dict[str, Any]],
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

        review_id = str(review.get("review_id", ""))
        material = refined_material_map.get(review_id, {})
        refined_text = str(material.get("refined_text", ""))
        snippet_source = refined_text if refined_text else str(review.get("review_text", ""))
        snippet = _prepare_evidence_source_text(snippet_source, limit=1200)
        if not snippet or snippet in seen:
            continue
        if _is_noisy_evidence_text(snippet):
            continue
        seen.add(snippet)

        item = {"review_id": review_id, "snippet": snippet}
        material_stance = str(material.get("stance", "")).strip().lower()
        if material_stance in {"positive", "negative"}:
            stance = material_stance
        else:
            stance = _classify_snippet_stance(snippet, voted_up=bool(review.get("voted_up", False)))
        if stance == "positive":
            positive.append(item)
        elif stance == "negative":
            negative.append(item)
        else:
            continue

        if len(positive) >= 4 and len(negative) >= 4:
            break

    if not positive and not negative:
        for index, snippet in enumerate(fallback_snippets[:3]):
            normalized = _prepare_evidence_source_text(str(snippet), limit=1200)
            if normalized and not _is_noisy_evidence_text(normalized):
                negative.append(
                    {
                        "review_id": f"fallback-{aspect}-{index + 1}",
                        "snippet": normalized,
                    }
                )

    return {"positive": positive[:4], "negative": negative[:4]}


def _build_refined_material_map(report_materials: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for material in list(report_materials or []):
        if not isinstance(material, dict):
            continue
        review_id = str(material.get("review_id", "")).strip()
        refined_text = str(material.get("refined_text", "")).strip()
        if not review_id or not refined_text:
            continue
        result[review_id] = {
            "refined_text": refined_text,
            "stance": str(material.get("stance", "")).strip().lower(),
        }
    return result


def _build_report_deterministic(consensus_payload: dict[str, Any]) -> dict[str, Any]:
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    high = [item for item in aspects if item.get("consensus_level") == "high"]
    medium = [item for item in aspects if item.get("consensus_level") == "medium"]

    selected_strengths = _select_strengths(high, medium)
    selected_risks = _select_risks(high, medium)
    recent_state = _derive_recent_state(selected_risks, high, medium)
    paid_recommendation = _derive_recommendation(selected_risks, recent_state["status"])
    recommendation = _to_price_aware_recommendation(
        paid_recommendation,
        is_free_game=_is_free_game(consensus_payload),
    )
    headline = _build_headline(recommendation, selected_strengths, selected_risks)
    buy_timing_summary = _build_timing_summary(recommendation, recent_state, selected_risks)
    evidence_blocks = _build_evidence_blocks(consensus_payload)

    good_for = _build_good_for(selected_strengths)
    not_good_for = _build_not_good_for(selected_risks)

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
        return {"status": "insufficient_data", "summary": "최근 후기만으로는 체감 변화를 단정하기 어려운 상태입니다."}

    up = sum(1 for item in selected_risks if item.get("recent_trend") == "up")
    down = sum(1 for item in selected_risks if item.get("recent_trend") == "down")

    if selected_risks and up >= down + 1:
        return {"status": "declining", "summary": "최근에는 불편을 호소하는 후기가 늘어 체감 만족도가 내려가는 흐름입니다."}
    if selected_risks and down >= up + 1:
        return {"status": "improving", "summary": "불편 요소 체감이 완화됐다는 후기가 늘어 플레이 경험이 나아지는 흐름입니다."}
    if selected_risks:
        return {"status": "mixed", "summary": "만족 포인트와 불편 포인트가 함께 보여 체감 평가가 갈리는 상태입니다."}
    return {"status": "stable", "summary": "최근 후기 체감은 큰 흔들림 없이 비슷한 수준으로 유지되는 편입니다."}


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
    strength_theme = _experience_theme(strengths[0], positive=True) if strengths else "핵심 플레이 감각"
    risk_theme = _experience_theme(risks[0], positive=False) if risks else "기술 안정성"

    if recommendation in {"free_play_recommended", "play_now"}:
        return f"{strength_theme} 체감이 좋아 무료로 지금 시작해보기 좋은 상태입니다."
    if recommendation == "try_lightly":
        return f"{strength_theme} 장점이 보여 무료로 가볍게 시작해보고 맞는지 판단하기 좋습니다."
    if recommendation == "buy_now":
        return f"{strength_theme} 체감이 좋아 지금 바로 시작해도 만족도가 높은 편입니다."
    if recommendation == "buy_on_sale":
        return f"{strength_theme} 장점은 분명하지만 {risk_theme}이 거슬릴 수 있어 할인 시점이 더 안전합니다."
    if recommendation == "wait":
        return f"{strength_theme}은 매력적이지만 {risk_theme} 불편이 남아 있어 업데이트를 본 뒤 결정하는 편이 좋습니다."
    return f"{risk_theme} 불편이 플레이 경험을 크게 흔들 수 있어 현재 시점 구매는 보수적으로 보는 편이 좋습니다."


def _build_timing_summary(
    recommendation: str,
    recent_state: dict[str, str],
    risks: list[dict[str, Any]],
) -> str:
    risk_theme = _experience_theme(risks[0], positive=False) if risks else "핵심 리스크"
    status = recent_state.get("status", "mixed")

    if recommendation in {"free_play_recommended", "play_now"}:
        return "무료 게임 기준으로 보면 지금 바로 플레이를 시작해도 체감 부담이 낮은 편입니다."
    if recommendation == "try_lightly":
        return "무료이므로 큰 진입 비용 없이 먼저 짧게 플레이해 취향 적합성을 확인하기 좋습니다."
    if recommendation == "buy_now":
        return "최근 후기 흐름에서 체감 불편이 크게 늘지 않아 지금 시작해도 부담이 낮은 편입니다."
    if recommendation == "buy_on_sale":
        return f"{risk_theme} 불편을 감수해야 할 수 있어 가격 메리트가 있는 시점이 더 낫습니다."
    if recommendation == "wait":
        if status == "declining":
            return f"{risk_theme} 관련 불편을 호소하는 후기가 늘어 업데이트 방향을 확인한 뒤 결정하는 편이 안전합니다."
        return f"{risk_theme} 불편이 여전히 자주 보이는 편이라 한두 번 더 패치 흐름을 보고 사는 것이 좋습니다."
    return f"{risk_theme} 문제가 플레이 몰입을 크게 깰 수 있어, 당장은 관망이 더 안전합니다."


def _build_good_for(selected_strengths: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in selected_strengths:
        aspect = str(item.get("aspect", ""))
        phrase = GOOD_FOR_SCENARIOS.get(aspect)
        if phrase and phrase not in result:
            result.append(phrase)
    if not result:
        result.append("한 번 시작하면 오래 몰입해 플레이할 수 있는 상황의 플레이어")
    return result


def _build_not_good_for(selected_risks: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in selected_risks:
        aspect = str(item.get("aspect", ""))
        phrase = NOT_GOOD_FOR_SCENARIOS.get(aspect)
        if phrase and phrase not in result:
            result.append(phrase)
    if not result:
        result.append("완성도와 기술 안정성이 조금만 흔들려도 스트레스를 크게 받는 플레이어")
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
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_positive_theme(themes)
    if selected_theme:
        return {
            "title": selected_theme,
            "summary": _strength_experience_summary(aspect=str(item.get("aspect", "")), theme=selected_theme),
        }
    return {
        "title": label,
        "summary": _strength_experience_summary(aspect=str(item.get("aspect", "")), theme=label),
    }


def _to_risk_item(item: dict[str, Any]) -> dict[str, str]:
    label = CATEGORY_DISPLAY.get(item["aspect"], item["aspect"])
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_negative_theme(themes)
    if selected_theme:
        return {
            "title": selected_theme,
            "summary": _risk_experience_summary(aspect=str(item.get("aspect", "")), theme=selected_theme),
        }
    return {
        "title": label,
        "summary": _risk_experience_summary(aspect=str(item.get("aspect", "")), theme=label),
    }


def _experience_theme(item: dict[str, Any], *, positive: bool) -> str:
    themes = list(item.get("themes", []) or [])
    selected = _choose_positive_theme(themes) if positive else _choose_negative_theme(themes)
    if selected:
        return selected
    return CATEGORY_DISPLAY.get(str(item.get("aspect", "")), "핵심 경험")


def _strength_experience_summary(*, aspect: str, theme: str) -> str:
    if aspect == "gameplay":
        return f"{theme} 체감이 좋아 한 판 더 하게 되는 흐름이 잘 만들어집니다."
    if aspect == "story":
        return f"{theme} 덕분에 진행을 멈추기 어려울 만큼 몰입감이 유지됩니다."
    if aspect == "graphics":
        return f"{theme}이 플레이 분위기를 끌어올려 감상형 플레이 만족도가 높습니다."
    if aspect == "customization":
        return f"{theme} 재미가 커서 캐릭터를 만지는 시간 자체가 즐거운 편입니다."
    if aspect == "content_depth":
        return f"{theme} 덕분에 장시간 플레이에서도 목표를 잃지 않기 쉽습니다."
    return f"{theme}이 실제 플레이 만족도로 이어지는 편입니다."


def _risk_experience_summary(*, aspect: str, theme: str) -> str:
    if aspect == "performance":
        return f"{theme} 때문에 전투나 이동 흐름이 끊겨 몰입이 쉽게 깨질 수 있습니다."
    if aspect == "bugs":
        return f"{theme}이 진행 리듬을 자주 끊어 플레이 피로를 높일 수 있습니다."
    if aspect in {"difficulty", "difficulty_onboarding"}:
        return f"{theme} 때문에 초반 적응에서 막히면 이탈 가능성이 커질 수 있습니다."
    if aspect == "monetization":
        return f"{theme}이 거슬리면 가격 대비 만족감이 빠르게 떨어질 수 있습니다."
    return f"{theme}이 플레이 경험의 만족도를 낮출 수 있어 주의가 필요합니다."


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
                "aspects": [],
                "aspect_labels": [],
                "snippets": [],
            },
        )

        bucket["mention_count"] += int(item.get("mention_count", 0))
        aspect = str(item.get("aspect", ""))
        if aspect and aspect not in bucket["aspects"]:
            bucket["aspects"].append(aspect)
        aspect_label = str(item.get("aspect_label", ""))
        if aspect_label and aspect_label not in bucket["aspect_labels"]:
            bucket["aspect_labels"].append(aspect_label)

        evidence_group = item.get("evidence_group", {}) or {}
        stance_snippets = list(evidence_group.get(stance, []) or [])
        match_tokens = _build_theme_match_tokens(bucket["theme"], bucket["aspects"])
        for snippet in stance_snippets:
            text = _prepare_evidence_source_text(str(snippet.get("snippet", "")), limit=1200)
            if not text or text in bucket["snippets"]:
                continue
            if not _snippet_matches_stance(text, stance):
                continue
            if match_tokens and not _snippet_matches_theme(text, match_tokens):
                continue
            bucket["snippets"].append(text)
            if len(bucket["snippets"]) >= 4:
                break

    blocks: list[dict[str, Any]] = []
    for bucket in sorted(grouped.values(), key=lambda b: (-int(b["mention_count"]), b["theme"])):
        if int(bucket["mention_count"]) < high_min:
            continue
        if len(bucket["snippets"]) < 2:
            continue

        title = _build_block_title(bucket["theme"], bucket["stance"])
        why_it_matters = _build_block_why_it_matters(
            stance=bucket["stance"],
            theme=bucket["theme"],
            aspect_labels=bucket["aspect_labels"],
        )
        blocks.append(
            {
                "title": title,
                "theme": bucket["theme"],
                "why_it_matters": why_it_matters,
                "explanation": why_it_matters,
                "aspect_keys": list(bucket["aspects"]),
                "stance": bucket["stance"],
                "consensus_level": "high",
                "mention_count": int(bucket["mention_count"]),
                "evidence_snippets": bucket["snippets"][:3],
            }
        )
        if len(blocks) >= 4:
            break
    return blocks


def _build_evidence_blocks_v2(consensus_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build insight+evidence blocks with 3-stage gates.

    Stage 1: strict (stance + theme match, high consensus first)
    Stage 2: relaxed (stance match + aspect-aligned material)
    Stage 3: guaranteed_fill (global stance pools to avoid empty evidence)
    """
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    high_min = int(
        (consensus_payload.get("consensus_thresholds", {}) or {}).get("high_min_mentions", 12)
    )
    high_items = [item for item in aspects if item.get("consensus_level") == "high"]
    medium_items = [item for item in aspects if item.get("consensus_level") == "medium"]
    base_items = high_items if high_items else medium_items
    if not base_items:
        return []

    pool_items = high_items + medium_items
    global_stance_snippets = _collect_global_stance_snippets_v2(pool_items)
    global_material_snippets = _collect_global_material_snippets_v2(consensus_payload)

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in base_items:
        stance = _block_stance(item)
        if stance not in {"positive", "negative"}:
            continue

        theme = _pick_block_theme(item, stance) or str(item.get("aspect_label", "?듭떖 ?섍껄"))
        key = (stance, theme)
        bucket = grouped.setdefault(
            key,
            {
                "stance": stance,
                "theme": theme,
                "mention_count": 0,
                "aspects": [],
                "aspect_labels": [],
                "consensus_level": str(item.get("consensus_level", "high")),
                "strict_candidates": [],
                "relaxed_candidates": [],
            },
        )

        bucket["mention_count"] += int(item.get("mention_count", 0))
        aspect = str(item.get("aspect", ""))
        if aspect and aspect not in bucket["aspects"]:
            bucket["aspects"].append(aspect)
        aspect_label = str(item.get("aspect_label", ""))
        if aspect_label and aspect_label not in bucket["aspect_labels"]:
            bucket["aspect_labels"].append(aspect_label)

        evidence_group = item.get("evidence_group", {}) or {}
        stance_snippets = list(evidence_group.get(stance, []) or [])
        match_tokens = _build_theme_match_tokens(bucket["theme"], bucket["aspects"])
        for snippet in stance_snippets:
            text = _prepare_evidence_source_text(str(snippet.get("snippet", "")), limit=1200)
            if not text:
                continue
            if not _snippet_matches_stance(text, stance):
                continue
            if match_tokens and _snippet_matches_theme(text, match_tokens):
                if text not in bucket["strict_candidates"]:
                    bucket["strict_candidates"].append(text)
            if text not in bucket["relaxed_candidates"]:
                bucket["relaxed_candidates"].append(text)

    blocks: list[dict[str, Any]] = []
    for bucket in sorted(grouped.values(), key=lambda b: (-int(b["mention_count"]), b["theme"])):
        if bucket.get("consensus_level") == "high" and int(bucket["mention_count"]) < high_min:
            continue

        stage = "strict"
        snippets: list[str] = []
        snippets = _append_unique_snippets_v2(
            snippets,
            list(bucket.get("strict_candidates", [])),
            limit=8,
        )

        if len(snippets) < 2:
            stage = "relaxed"
            snippets = _append_unique_snippets_v2(
                snippets,
                list(bucket.get("relaxed_candidates", [])),
                limit=8,
            )
            snippets = _append_unique_snippets_v2(
                snippets,
                _collect_aspect_material_snippets_v2(
                    consensus_payload=consensus_payload,
                    stance=str(bucket.get("stance", "")),
                    aspects=list(bucket.get("aspects", [])),
                ),
                limit=8,
            )

        if len(snippets) < 2:
            stage = "guaranteed_fill"
            stance_key = str(bucket.get("stance", ""))
            snippets = _append_unique_snippets_v2(
                snippets,
                list(global_stance_snippets.get(stance_key, [])),
                limit=8,
            )
            snippets = _append_unique_snippets_v2(
                snippets,
                list(global_material_snippets.get(stance_key, [])),
                limit=8,
            )

        if len(snippets) < 2:
            continue

        title = _build_block_title(str(bucket["theme"]), str(bucket["stance"]))
        why_it_matters = _build_block_why_it_matters(
            stance=str(bucket["stance"]),
            theme=str(bucket["theme"]),
            aspect_labels=list(bucket["aspect_labels"]),
        )
        blocks.append(
            {
                "title": title,
                "theme": str(bucket["theme"]),
                "why_it_matters": why_it_matters,
                "explanation": why_it_matters,
                "aspect_keys": list(bucket["aspects"]),
                "stance": str(bucket["stance"]),
                "consensus_level": str(bucket.get("consensus_level", "high")),
                "mention_count": int(bucket["mention_count"]),
                "evidence_quality_level": stage,
                "evidence_candidate_snippets": snippets[:8],
                "evidence_snippets": snippets[:3],
            }
        )
        if len(blocks) >= 4:
            break

    blocks = _ensure_min_stance_blocks_v2(
        blocks=blocks,
        source_items=pool_items,
        global_stance_snippets=global_stance_snippets,
        global_material_snippets=global_material_snippets,
    )
    return blocks


def _append_unique_snippets_v2(base: list[str], incoming: list[str], *, limit: int) -> list[str]:
    result = list(base)
    seen = set(result)
    for text in incoming:
        normalized = _prepare_evidence_source_text(str(text), limit=1200)
        if not normalized or normalized in seen:
            continue
        if _is_noisy_evidence_text(normalized):
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def _collect_global_stance_snippets_v2(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    collected = {"positive": [], "negative": []}
    for item in items:
        for stance in ("positive", "negative"):
            evidence_group = item.get("evidence_group", {}) or {}
            for snippet in list(evidence_group.get(stance, []) or []):
                text = _prepare_evidence_source_text(str(snippet.get("snippet", "")), limit=1200)
                if not text:
                    continue
                if not _snippet_matches_stance(text, stance):
                    continue
                if text not in collected[stance]:
                    collected[stance].append(text)
    return collected


def _collect_global_material_snippets_v2(consensus_payload: dict[str, Any]) -> dict[str, list[str]]:
    collected = {"positive": [], "negative": []}
    for material in list(consensus_payload.get("report_materials", []) or []):
        if not isinstance(material, dict):
            continue
        stance = str(material.get("stance", "")).strip().lower()
        if stance not in {"positive", "negative"}:
            continue
        text = _prepare_evidence_source_text(str(material.get("refined_text", "")), limit=1200)
        if not text:
            continue
        if text not in collected[stance]:
            collected[stance].append(text)
    return collected


def _collect_aspect_material_snippets_v2(
    *,
    consensus_payload: dict[str, Any],
    stance: str,
    aspects: list[str],
) -> list[str]:
    aspect_set = {str(aspect).strip().lower() for aspect in aspects if str(aspect).strip()}
    if not aspect_set:
        return []

    result: list[str] = []
    for material in list(consensus_payload.get("report_materials", []) or []):
        if not isinstance(material, dict):
            continue
        material_stance = str(material.get("stance", "")).strip().lower()
        if material_stance != stance:
            continue
        material_tags = {
            str(tag).strip().lower()
            for tag in list(material.get("category_tags", []) or [])
            if str(tag).strip()
        }
        if material_tags and aspect_set.isdisjoint(material_tags):
            continue
        text = _prepare_evidence_source_text(str(material.get("refined_text", "")), limit=1200)
        if text:
            result.append(text)
    return result


def _ensure_min_stance_blocks_v2(
    *,
    blocks: list[dict[str, Any]],
    source_items: list[dict[str, Any]],
    global_stance_snippets: dict[str, list[str]],
    global_material_snippets: dict[str, list[str]],
) -> list[dict[str, Any]]:
    result = list(blocks)
    existing = {str(block.get("stance", "")) for block in result}
    for stance in ("positive", "negative"):
        if stance in existing:
            continue
        candidate = _pick_best_item_for_stance_v2(source_items, stance)
        if not candidate:
            continue
        snippets: list[str] = []
        snippets = _append_unique_snippets_v2(snippets, list(global_stance_snippets.get(stance, [])), limit=8)
        snippets = _append_unique_snippets_v2(snippets, list(global_material_snippets.get(stance, [])), limit=8)
        if len(snippets) < 2:
            continue

        theme = _pick_block_theme(candidate, stance) or str(candidate.get("aspect_label", "?듭떖 ?섍껄"))
        aspect_label = str(candidate.get("aspect_label", ""))
        why = _build_block_why_it_matters(
            stance=stance,
            theme=theme,
            aspect_labels=[aspect_label] if aspect_label else [],
        )
        result.append(
            {
                "title": _build_block_title(theme, stance),
                "theme": theme,
                "why_it_matters": why,
                "explanation": why,
                "aspect_keys": [str(candidate.get("aspect", ""))],
                "stance": stance,
                "consensus_level": str(candidate.get("consensus_level", "medium")),
                "mention_count": int(candidate.get("mention_count", 0)),
                "evidence_quality_level": "guaranteed_fill",
                "evidence_candidate_snippets": snippets[:8],
                "evidence_snippets": snippets[:3],
            }
        )
    return result


def _pick_best_item_for_stance_v2(items: list[dict[str, Any]], stance: str) -> dict[str, Any] | None:
    candidates = [item for item in items if _block_stance(item) == stance]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            -_consensus_rank(str(item.get("consensus_level", "low"))),
            -int(item.get("mention_count", 0)),
        ),
    )[0]


# Use v2 generator as the active evidence strategy.
_build_evidence_blocks = _build_evidence_blocks_v2


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


def _build_block_title(theme: str, stance: str) -> str:
    if stance == "positive":
        return f"{theme}이 실제 플레이 만족으로 이어진다는 반응"
    return f"{theme} 때문에 플레이 흐름이 끊긴다는 반응"


def _build_block_why_it_matters(
    *,
    stance: str,
    theme: str,
    aspect_labels: list[str],
) -> str:
    aspect_text = ", ".join(aspect_labels[:2]) if aspect_labels else "핵심 플레이"
    if stance == "negative":
        return f"{aspect_text}에서 {theme} 불편이 반복되면 초반 만족도가 크게 떨어질 수 있어 구매 전 감수 여부 확인이 필요합니다."
    return (
        f"{aspect_text}에서 {theme} 체감이 좋으면 초반부터 몰입이 붙어 장시간 플레이 만족으로 이어질 가능성이 큽니다."
    )


def _theme_tokens(theme: str) -> list[str]:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣 ]", " ", str(theme)).lower()
    tokens = [token.strip() for token in cleaned.split() if len(token.strip()) >= 2]
    return list(dict.fromkeys(tokens))


def _aspect_hint_tokens(aspects: list[str]) -> list[str]:
    tokens: list[str] = []
    for aspect in aspects:
        key = str(aspect or "").strip().lower()
        if not key:
            continue
        for token in ASPECT_EVIDENCE_HINTS.get(key, ()):
            token_text = str(token).strip().lower()
            if len(token_text) >= 2:
                tokens.append(token_text)
    return list(dict.fromkeys(tokens))


def _build_theme_match_tokens(theme: str, aspects: list[str]) -> list[str]:
    merged = _theme_tokens(theme) + _aspect_hint_tokens(aspects)
    return list(dict.fromkeys(merged))


def _snippet_matches_theme(text: str, theme_tokens: list[str]) -> bool:
    if not theme_tokens:
        return True
    normalized = str(text).lower().replace(" ", "")
    return any(token.replace(" ", "") in normalized for token in theme_tokens)


def _snippet_matches_stance(text: str, stance: str) -> bool:
    normalized = str(text).lower()
    pos_hits = sum(1 for token in EVIDENCE_POSITIVE_HINTS if token in normalized)
    neg_hits = sum(1 for token in EVIDENCE_NEGATIVE_HINTS if token in normalized)
    if stance == "positive":
        if pos_hits == 0 and neg_hits == 0:
            return True
        return pos_hits > neg_hits
    if stance == "negative":
        if pos_hits == 0 and neg_hits == 0:
            return True
        return neg_hits > pos_hits
    return True


def _classify_snippet_stance(text: str, *, voted_up: bool) -> str:
    normalized = str(text).lower()
    pos_hits = sum(1 for token in EVIDENCE_POSITIVE_HINTS if token in normalized)
    neg_hits = sum(1 for token in EVIDENCE_NEGATIVE_HINTS if token in normalized)
    if pos_hits >= neg_hits + 1:
        return "positive"
    if neg_hits >= pos_hits + 1:
        return "negative"
    return "positive" if voted_up else "negative"


def _compress_evidence_sections(
    evidence_sections: dict[str, list[dict[str, Any]]],
    *,
    use_llm: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Select grouped evidence snippets with judge-only replacement."""
    strengths = list(evidence_sections.get("strengths", []) or [])
    risks = list(evidence_sections.get("risks", []) or [])
    if not strengths and not risks:
        return {"strengths": [], "risks": []}

    judge = (
        OpenAIEvidenceJudge()
        if use_llm and _should_use_llm_evidence_judge()
        else None
    )
    llm_judge_enabled = bool(judge and judge.available)

    def _compress_block_list(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compressed_blocks: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            snippets = block.get("evidence_snippets")
            if not isinstance(snippets, list):
                continue
            candidate_snippets = block.get("evidence_candidate_snippets")
            source_snippets = (
                list(candidate_snippets)
                if isinstance(candidate_snippets, list) and candidate_snippets
                else list(snippets)
            )
            if not source_snippets:
                continue
            stance = str(block.get("stance", "mixed"))
            match_tokens = _build_theme_match_tokens(
                str(block.get("theme", "")),
                [str(item) for item in list(block.get("aspect_keys", []) or [])],
            )

            rewritten: list[str] = []
            seen: set[str] = set()
            for raw in source_snippets[:8]:
                raw_text = str(raw or "").strip()
                if not raw_text:
                    continue

                normalized = _prepare_evidence_source_text(raw_text, limit=1200)
                if not normalized:
                    continue
                if _is_noisy_evidence_text(normalized):
                    continue
                if not _snippet_matches_stance(normalized, stance):
                    continue
                if match_tokens and not _snippet_matches_theme(normalized, match_tokens):
                    continue

                if normalized not in seen:
                    seen.add(normalized)
                    rewritten.append(normalized)
                if len(rewritten) >= 8:
                    break

            if len(rewritten) < 2:
                fallback_rewritten: list[str] = []
                fallback_seen: set[str] = set()
                for raw in source_snippets[:8]:
                    raw_text = str(raw or "").strip()
                    if not raw_text:
                        continue
                    normalized = _prepare_evidence_source_text(raw_text, limit=1200)
                    if not normalized:
                        continue
                    if normalized in fallback_seen:
                        continue
                    if not _snippet_matches_stance(normalized, stance):
                        continue
                    fallback_seen.add(normalized)
                    fallback_rewritten.append(normalized)
                    if len(fallback_rewritten) >= 8:
                        break
                if len(fallback_rewritten) >= 2:
                    rewritten = fallback_rewritten[:8]
            if len(rewritten) < 2:
                continue

            finalized = _select_evidence_snippets_for_block(
                block=block,
                candidates=rewritten[:8],
                judge=(judge if llm_judge_enabled else None),
            )
            if len(finalized) < 2:
                finalized = _rank_evidence_candidates(
                    candidates=rewritten[:8],
                    stance=stance,
                    match_tokens=match_tokens,
                )[:3]
            if len(finalized) < 2:
                continue
            next_block = dict(block)
            next_block["evidence_candidate_snippets"] = rewritten[:8]
            next_block["evidence_snippets"] = finalized[:3]
            compressed_blocks.append(next_block)
        return compressed_blocks

    return {
        "strengths": _compress_block_list(strengths)[:3],
        "risks": _compress_block_list(risks)[:3],
    }


def _select_evidence_snippets_for_block(
    *,
    block: dict[str, Any],
    candidates: list[str],
    judge: OpenAIEvidenceJudge | None,
) -> list[str]:
    stance = str(block.get("stance", "mixed"))
    match_tokens = _build_theme_match_tokens(
        str(block.get("theme", "")),
        [str(item) for item in list(block.get("aspect_keys", []) or [])],
    )
    ranked = _rank_evidence_candidates(candidates=candidates, stance=stance, match_tokens=match_tokens)
    if len(ranked) < 2:
        return ranked

    preferred: list[str] = []
    if judge is not None and len(ranked) >= 2:
        selected_indices = judge.judge(
            title=str(block.get("title", "핵심 근거")),
            theme=str(block.get("theme", "")),
            why_it_matters=str(block.get("why_it_matters", "")),
            stance=stance,
            candidates=ranked[:8],
            timeout_seconds=20,
            retry_limit=1,
        )
        if selected_indices:
            for index in selected_indices:
                zero_based = index - 1
                if 0 <= zero_based < len(ranked):
                    preferred.append(ranked[zero_based])

    ordered: list[str] = []
    seen: set[str] = set()
    for text in preferred + ranked:
        if text in seen:
            continue
        seen.add(text)
        ordered.append(text)

    strict: list[str] = []
    for text in ordered:
        if not _snippet_matches_stance(text, stance):
            continue
        if match_tokens and not _snippet_matches_theme(text, match_tokens):
            continue
        strict.append(text)
        if len(strict) >= 3:
            break
    if len(strict) >= 2:
        return strict[:3]

    relaxed = list(strict)
    for text in ordered:
        if text in relaxed:
            continue
        if not _snippet_matches_stance(text, stance):
            continue
        relaxed.append(text)
        if len(relaxed) >= 3:
            break
    if len(relaxed) >= 2:
        return relaxed[:3]

    fallback = list(relaxed)
    for text in ordered:
        if text in fallback:
            continue
        fallback.append(text)
        if len(fallback) >= 3:
            break
    return fallback[:3] if len(fallback) >= 2 else []


def _rank_evidence_candidates(
    *,
    candidates: list[str],
    stance: str,
    match_tokens: list[str],
) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, text in enumerate(candidates):
        normalized = str(text).strip()
        if not normalized:
            continue
        score = 0
        if _snippet_matches_stance(normalized, stance):
            score += 4
        if match_tokens and _snippet_matches_theme(normalized, match_tokens):
            score += 2
        if 20 <= len(normalized) <= 320:
            score += 1
        scored.append((score, index, normalized))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored]


def _compress_evidence_reviews(
    report_payload: dict[str, Any],
    *,
    use_llm: bool,
) -> dict[str, Any]:
    """Backward-compat wrapper for old flat payload shape."""
    evidence_blocks = report_payload.get("evidence_reviews")
    if not isinstance(evidence_blocks, list):
        return report_payload
    sections = _build_evidence_sections_from_blocks(evidence_blocks)
    compressed = _compress_evidence_sections(sections, use_llm=use_llm)
    merged_blocks = list(compressed.get("strengths", [])) + list(compressed.get("risks", []))
    next_payload = dict(report_payload)
    next_payload["evidence_reviews"] = merged_blocks
    return next_payload


def _attach_evidence_sections(report_payload: dict[str, Any]) -> dict[str, Any]:
    """Backward-compat helper; maps old flat evidence into new section map."""
    blocks = report_payload.get("evidence_reviews")
    if not isinstance(blocks, list):
        next_payload = dict(report_payload)
        next_payload["evidence_sections"] = {"strengths": [], "risks": []}
        return next_payload

    next_payload = dict(report_payload)
    next_payload["evidence_sections"] = _build_evidence_sections_from_blocks(blocks)
    return next_payload


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


def _is_noisy_evidence_text(text: str) -> bool:
    target = " ".join((text or "").split()).strip()
    if not target:
        return True
    if len(target) < 18:
        return True
    compact = target.replace(" ", "")
    if not compact:
        return True
    if re.search(r"(.)\1{6,}", compact):
        return True
    jamo_count = len(re.findall(r"[ㄱ-ㅎㅏ-ㅣ]", compact))
    if jamo_count >= 8:
        return True
    readable = len(re.findall(r"[0-9A-Za-z가-힣]", compact))
    if readable / max(len(compact), 1) < 0.55:
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
        if not isinstance(item.get("why_it_matters"), str):
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
    strengths = value.get("strengths")
    risks = value.get("risks")
    if not _is_evidence_block_list(strengths):
        return False
    if not _is_evidence_block_list(risks):
        return False
    if any(item.get("stance") != "positive" for item in strengths):
        return False
    if any(item.get("stance") != "negative" for item in risks):
        return False
    return True
