"""Consumer-facing purchase decision report builders."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from models.schemas import AnalysisResult, GameMetadata, ProcessedReview, RawReview
from services.evidence_relevance_judge import OpenAIEvidenceRelevanceJudge
from services.evidence_snippet_llm import OpenAIEvidenceSnippetCompressor
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


def _should_use_llm_evidence_compression() -> bool:
    return os.getenv("USE_LLM_EVIDENCE_COMPRESSION", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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
    evidence_sections = _apply_evidence_relevance_judge(
        evidence_sections=evidence_sections,
        consensus_payload=consensus_payload,
        use_llm=bool(enable_llm_sections),
    )
    evidence_sections = _truncate_evidence_sections_by_plan(evidence_sections, report_plan)
    evidence_sections = _ensure_non_empty_evidence_sections(
        evidence_sections=evidence_sections,
        consensus_payload=consensus_payload,
        report_plan=report_plan,
        report_display=report_display,
    )

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
    fallback["evidence_sections"] = _ensure_non_empty_evidence_sections(
        evidence_sections=dict(fallback.get("evidence_sections", {}) or {}),
        consensus_payload=consensus_payload,
        report_plan=seed_plan,
        report_display=dict(fallback.get("report_display", {}) or {}),
    )
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
        report_display["headline"] = _fix(
            _rewrite_headline_as_advice(
                report_display=report_display,
                report_plan=report_plan,
                is_free_game=is_free_game,
            )
        )
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
    strength_priorities = list((report_plan.get("theme_priorities", {}) or {}).get("strengths", []) or [])
    for item in list(report_display.get("top_strengths", []) or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        aspect = ""
        if len(strength_priorities) > len(top_strengths) and isinstance(
            strength_priorities[len(top_strengths)], dict
        ):
            aspect = str(strength_priorities[len(top_strengths)].get("aspect", ""))
        next_item["title"] = _fix(_strength_outcome_title(aspect=aspect or "gameplay"))
        if isinstance(next_item.get("summary"), str):
            next_item["summary"] = _fix(str(next_item.get("summary", "")))
        top_strengths.append(next_item)
    report_display["top_strengths"] = top_strengths

    top_risks = []
    risk_priorities = list((report_plan.get("theme_priorities", {}) or {}).get("risks", []) or [])
    for item in list(report_display.get("top_risks", []) or []):
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        aspect = ""
        if len(risk_priorities) > len(top_risks) and isinstance(risk_priorities[len(top_risks)], dict):
            aspect = str(risk_priorities[len(top_risks)].get("aspect", ""))
        next_item["title"] = _fix(_risk_outcome_title(aspect=aspect or "performance"))
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
            full_texts = [str(item) for item in list(next_block.get("evidence_full_text", []) or []) if str(item)]
            if not full_texts:
                full_texts = [str(item) for item in list(next_block.get("evidence_snippets", []) or []) if str(item)]
            pair_count = min(len(next_block["evidence_snippets"]), len(full_texts))
            next_block["evidence_snippets"] = list(next_block["evidence_snippets"])[:pair_count]
            next_block["evidence_full_text"] = full_texts[:pair_count]
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


def _strength_outcome_title(*, aspect: str) -> str:
    key = str(aspect or "").strip().lower()
    mapping = {
        "difficulty": "처음에는 어렵지만, 반복 플레이를 통해 실력이 눈에 띄게 늘어나는 구조",
        "difficulty_onboarding": "초반에 헤맬 수 있지만, 흐름을 익히면 플레이 리듬이 빠르게 붙는 구조",
        "gameplay": "전투 리듬에 익숙해질수록 손에 붙는 재미가 커지는 구조",
        "story": "진행할수록 서사 몰입이 깊어져 한 챕터를 더 넘기게 되는 구조",
        "graphics": "플레이를 이어갈수록 월드 연출의 몰입감이 커지는 구조",
        "content_depth": "짧게 끝나지 않고, 할수록 파고들 거리가 늘어나는 구조",
        "customization": "시간을 들일수록 내 취향에 맞는 플레이 스타일이 완성되는 구조",
    }
    return mapping.get(key, "진행할수록 장점이 체감되는 플레이 경험")


def _risk_outcome_title(*, aspect: str) -> str:
    key = str(aspect or "").strip().lower()
    mapping = {
        "performance": "교전이 치열해질수록 끊김이 체감되어 흐름이 깨질 수 있는 구조",
        "bugs": "몰입 중 예기치 않은 오류로 진행 리듬이 멈출 수 있는 구조",
        "difficulty": "초반 적응 구간에서 좌절감을 크게 느낄 수 있는 구조",
        "difficulty_onboarding": "핵심 규칙을 스스로 파악해야 해 초반 피로가 커질 수 있는 구조",
        "monetization": "비용 대비 만족을 엄격히 보면 아쉬움이 남을 수 있는 구조",
        "matchmaking": "매칭 품질이 흔들리면 플레이 만족이 크게 내려갈 수 있는 구조",
    }
    return mapping.get(key, "플레이 과정에서 피로가 누적될 수 있는 리스크 구조")


def _positive_headline_clause(aspect: str) -> str:
    key = str(aspect or "").strip().lower()
    mapping = {
        "gameplay": "손에 익기 시작하면 전투 몰입이 빠르게 올라오고",
        "difficulty": "초반 벽을 넘기면 실력 상승 체감이 크게 돌아오고",
        "difficulty_onboarding": "초반 적응만 지나면 플레이 속도가 눈에 띄게 붙고",
        "story": "진행할수록 스토리 몰입이 깊어지고",
        "graphics": "플레이할수록 월드 연출의 몰입감이 살아나고",
        "content_depth": "짧게 끝나지 않아 오래 붙잡고 즐기기 좋고",
    }
    return mapping.get(key, "진행할수록 장점 체감이 커지고")


def _negative_headline_clause(aspect: str) -> str:
    key = str(aspect or "").strip().lower()
    mapping = {
        "performance": "교전이 길어질 때 성능 변동으로 답답함이 생길 수 있습니다.",
        "bugs": "진행 중 오류가 나오면 몰입이 쉽게 끊길 수 있습니다.",
        "difficulty": "초반 적응 구간에서 좌절감이 크게 올 수 있습니다.",
        "difficulty_onboarding": "핵심 규칙 안내가 부족해 초반 피로가 높을 수 있습니다.",
        "monetization": "비용 대비 만족 기준이 높은 플레이어에게는 아쉬움이 남을 수 있습니다.",
    }
    return mapping.get(key, "일부 구간에서 피로를 느낄 가능성은 남아 있습니다.")


def _rewrite_headline_as_advice(
    *,
    report_display: dict[str, Any],
    report_plan: dict[str, Any],
    is_free_game: bool,
) -> str:
    recommendation = str(report_display.get("buy_recommendation", "")).strip()
    priorities = report_plan.get("theme_priorities", {}) if isinstance(report_plan, dict) else {}
    strength_aspect = ""
    risk_aspect = ""
    strengths = list(priorities.get("strengths", []) or [])
    risks = list(priorities.get("risks", []) or [])
    if strengths and isinstance(strengths[0], dict):
        strength_aspect = str(strengths[0].get("aspect", "")).strip()
    if risks and isinstance(risks[0], dict):
        risk_aspect = str(risks[0].get("aspect", "")).strip()

    positive = _positive_headline_clause(strength_aspect)
    negative = _negative_headline_clause(risk_aspect)

    if recommendation in {"free_play_recommended", "play_now"}:
        return f"초반에는 변수로 답답할 수 있지만, {positive} 지금 무료로 시작해볼 가치는 충분합니다."
    if recommendation == "try_lightly":
        return f"처음엔 적응이 필요할 수 있지만, {positive} 무료로 짧게 시작해 맞는지 확인해보는 선택이 안전합니다."
    if recommendation == "buy_now":
        return f"초반 적응 비용은 조금 있지만, {positive} 지금 구매해도 후회 가능성은 낮은 편입니다."
    if recommendation == "buy_on_sale":
        return f"{positive} {negative} 할인 구간에서 진입하면 만족 대비 리스크를 더 잘 관리할 수 있습니다."
    if recommendation == "wait":
        return f"{positive} 다만 {negative} 업데이트 방향을 한 번 더 확인한 뒤 결정하는 편이 안전합니다."
    return f"{positive} 다만 {negative} 지금은 구매보다 관망이 더 합리적인 선택에 가깝습니다."


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
        full_texts = [str(item) for item in list(block.get("evidence_full_text", []) or []) if str(item)]
        if not full_texts:
            full_texts = list(snippets)
        pair_count = min(len(snippets), len(full_texts))
        if pair_count < 2:
            continue
        snippets = snippets[:pair_count]
        full_texts = full_texts[:pair_count]
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
                    "evidence_snippets": snippets[:3],
                    "evidence_full_text": full_texts[:3],
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
                    "evidence_snippets": snippets[:3],
                    "evidence_full_text": full_texts[:3],
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
        snippets = list(block.get("evidence_snippets", []) or [])
        full_texts = list(block.get("evidence_full_text", []) or []) or list(snippets)
        clip = min(max(evidence_per_block, 0), len(snippets), len(full_texts))
        next_block["evidence_snippets"] = snippets[:clip]
        next_block["evidence_full_text"] = full_texts[:clip]
        clipped_strengths.append(next_block)

    clipped_risks = []
    for block in list(evidence_sections.get("risks", []) or [])[: max(risk_count, 0)]:
        next_block = dict(block)
        snippets = list(block.get("evidence_snippets", []) or [])
        full_texts = list(block.get("evidence_full_text", []) or []) or list(snippets)
        clip = min(max(evidence_per_block, 0), len(snippets), len(full_texts))
        next_block["evidence_snippets"] = snippets[:clip]
        next_block["evidence_full_text"] = full_texts[:clip]
        clipped_risks.append(next_block)

    return {
        "strengths": clipped_strengths,
        "risks": clipped_risks,
    }


def _ensure_non_empty_evidence_sections(
    *,
    evidence_sections: dict[str, list[dict[str, Any]]],
    consensus_payload: dict[str, Any],
    report_plan: dict[str, Any],
    report_display: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    strengths = list(evidence_sections.get("strengths", []) or [])
    risks = list(evidence_sections.get("risks", []) or [])

    if not strengths:
        fallback = _build_fallback_evidence_block(
            stance="positive",
            consensus_payload=consensus_payload,
            report_plan=report_plan,
            report_display=report_display,
            block_id="str_1",
        )
        if fallback is not None:
            strengths = [fallback]

    if not risks:
        fallback = _build_fallback_evidence_block(
            stance="negative",
            consensus_payload=consensus_payload,
            report_plan=report_plan,
            report_display=report_display,
            block_id="risk_1",
        )
        if fallback is not None:
            risks = [fallback]

    return {"strengths": strengths[:3], "risks": risks[:3]}


def _build_fallback_evidence_block(
    *,
    stance: str,
    consensus_payload: dict[str, Any],
    report_plan: dict[str, Any],
    report_display: dict[str, Any],
    block_id: str,
) -> dict[str, Any] | None:
    theme, aspect = _pick_priority_theme_and_aspect(
        stance=stance,
        report_plan=report_plan,
        report_display=report_display,
    )
    match_tokens = _build_theme_match_tokens(theme, [aspect] if aspect else [])
    snippets = _select_relaxed_evidence_snippets(
        consensus_payload=consensus_payload,
        stance=stance,
        match_tokens=match_tokens,
        minimum=2,
        maximum=3,
    )
    if len(snippets) < 2:
        return None

    title = (
        _strength_outcome_title(aspect=aspect or "gameplay")
        if stance == "positive"
        else _risk_outcome_title(aspect=aspect or "performance")
    )
    why_it_matters = _build_block_why_it_matters(
        stance=stance,
        theme=theme or ("핵심 장점" if stance == "positive" else "핵심 리스크"),
        aspect_labels=[CATEGORY_DISPLAY.get(aspect or "", "핵심 경험")],
    )
    return {
        "block_id": block_id,
        "title": title,
        "theme": theme,
        "why_it_matters": why_it_matters,
        "explanation": why_it_matters,
        "aspect_keys": [aspect] if aspect else [],
        "stance": stance,
        "consensus_level": "medium",
        "mention_count": len(snippets),
        "evidence_snippets": snippets[:3],
        "evidence_full_text": snippets[:3],
    }


def _pick_priority_theme_and_aspect(
    *,
    stance: str,
    report_plan: dict[str, Any],
    report_display: dict[str, Any],
) -> tuple[str, str]:
    priorities = report_plan.get("theme_priorities", {}) if isinstance(report_plan, dict) else {}
    key = "strengths" if stance == "positive" else "risks"
    top = list(priorities.get(key, []) or [])
    if top and isinstance(top[0], dict):
        return (
            str(top[0].get("theme", "")).strip(),
            str(top[0].get("aspect", "")).strip(),
        )

    display_key = "top_strengths" if stance == "positive" else "top_risks"
    display_items = list(report_display.get(display_key, []) or [])
    if display_items and isinstance(display_items[0], dict):
        return (
            str(display_items[0].get("title", "")).strip(),
            "",
        )
    return "", ""


def _select_relaxed_evidence_snippets(
    *,
    consensus_payload: dict[str, Any],
    stance: str,
    match_tokens: list[str],
    minimum: int,
    maximum: int,
) -> list[str]:
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    strict: list[tuple[int, int, str]] = []
    relaxed: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    index = 0

    for item in aspects:
        evidence_group = item.get("evidence_group", {}) or {}
        for entry in list(evidence_group.get(stance, []) or []):
            raw = _prepare_evidence_source_text(str(entry.get("snippet", "")), limit=1200)
            if not raw:
                continue
            normalized = _normalize_compressed_snippet(raw)
            if not normalized or _looks_cutoff(normalized) or _is_noisy_evidence_text(normalized):
                continue
            if normalized in seen:
                continue
            if not _snippet_matches_stance(normalized, stance):
                continue
            seen.add(normalized)
            score = _snippet_theme_overlap_score(normalized, match_tokens)
            strict.append((score, -index, normalized))
            index += 1

        for raw_sample in list(item.get("sample_reviews", []) or []):
            raw = _prepare_evidence_source_text(str(raw_sample), limit=1200)
            if not raw:
                continue
            normalized = _normalize_compressed_snippet(raw)
            if not normalized or _looks_cutoff(normalized) or _is_noisy_evidence_text(normalized):
                continue
            if normalized in seen:
                continue
            if not _snippet_matches_stance(normalized, stance):
                continue
            seen.add(normalized)
            score = _snippet_theme_overlap_score(normalized, match_tokens)
            strict.append((score, -index, normalized))
            index += 1

    strict.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [value for _, _, value in strict][:maximum]
    if len(selected) >= minimum:
        return selected[:maximum]

    # Relax: allow any readable snippet when strict theme match is not enough.
    for item in aspects:
        evidence_group = item.get("evidence_group", {}) or {}
        for bucket in ("positive", "negative"):
            for entry in list(evidence_group.get(bucket, []) or []):
                raw = _prepare_evidence_source_text(str(entry.get("snippet", "")), limit=1200)
                if not raw:
                    continue
                normalized = _normalize_compressed_snippet(raw)
                if not normalized or _looks_cutoff(normalized) or _is_noisy_evidence_text(normalized):
                    continue
                if normalized in seen:
                    continue
                stance_score = 2 if _snippet_matches_stance(normalized, stance) else 0
                theme_score = _snippet_theme_overlap_score(normalized, match_tokens)
                relaxed.append((stance_score, theme_score, -index, normalized))
                index += 1
                seen.add(normalized)

    relaxed.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    for stance_score, _, _, snippet in relaxed:
        if len(selected) >= maximum:
            break
        # Priority: stance match first, then approximate theme.
        if stance_score >= 1 or len(selected) < minimum:
            selected.append(snippet)

    return selected[:maximum]


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
                "sample_reviews": [str(item) for item in list(signal.get("sample_reviews", []) or []) if str(item)][:3],
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

        full_text = " ".join(str(review.get("review_text", "")).split()).strip()
        snippet = _prepare_evidence_source_text(full_text, limit=1200)
        if not snippet or not full_text or full_text in seen:
            continue
        if _is_noisy_evidence_text(snippet):
            continue
        seen.add(full_text)

        item = {
            "review_id": str(review.get("review_id", "")),
            "snippet": snippet,
            "full_text": full_text,
        }
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
            full_text = " ".join(str(snippet).split()).strip()
            normalized = _prepare_evidence_source_text(full_text, limit=1200)
            if normalized and full_text and not _is_noisy_evidence_text(normalized):
                negative.append(
                    {
                        "review_id": f"fallback-{aspect}-{index + 1}",
                        "snippet": normalized,
                        "full_text": full_text,
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
    strength_aspect = str(strengths[0].get("aspect", "")) if strengths else ""
    risk_aspect = str(risks[0].get("aspect", "")) if risks else ""
    positive = _positive_headline_clause(strength_aspect)
    negative = _negative_headline_clause(risk_aspect)

    if recommendation in {"free_play_recommended", "play_now"}:
        return f"초반에는 변수로 답답할 수 있지만, {positive} 지금 무료로 시작해볼 가치는 충분합니다."
    if recommendation == "try_lightly":
        return f"처음엔 적응이 필요할 수 있지만, {positive} 무료로 짧게 시작해 맞는지 확인해보는 선택이 안전합니다."
    if recommendation == "buy_now":
        return f"초반 적응 비용은 조금 있지만, {positive} 지금 구매해도 후회 가능성은 낮은 편입니다."
    if recommendation == "buy_on_sale":
        return f"{positive} {negative} 할인 구간에서 진입하면 만족 대비 리스크를 더 잘 관리할 수 있습니다."
    if recommendation == "wait":
        return f"{positive} 다만 {negative} 업데이트 방향을 한 번 더 확인한 뒤 결정하는 편이 안전합니다."
    return f"{positive} 다만 {negative} 지금은 구매보다 관망이 더 합리적인 선택에 가깝습니다."


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
    aspect = str(item.get("aspect", ""))
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_positive_theme(themes)
    title = _strength_outcome_title(aspect=aspect)
    if selected_theme:
        return {
            "title": title,
            "summary": _strength_experience_summary(aspect=aspect, theme=selected_theme),
        }
    return {
        "title": title,
        "summary": _strength_experience_summary(aspect=aspect, theme=CATEGORY_DISPLAY.get(aspect, "핵심 경험")),
    }


def _to_risk_item(item: dict[str, Any]) -> dict[str, str]:
    aspect = str(item.get("aspect", ""))
    themes = list(item.get("themes", []) or [])
    selected_theme = _choose_negative_theme(themes)
    title = _risk_outcome_title(aspect=aspect)
    if selected_theme:
        return {
            "title": title,
            "summary": _risk_experience_summary(aspect=aspect, theme=selected_theme),
        }
    return {
        "title": title,
        "summary": _risk_experience_summary(aspect=aspect, theme=CATEGORY_DISPLAY.get(aspect, "핵심 리스크")),
    }


def _experience_theme(item: dict[str, Any], *, positive: bool) -> str:
    themes = list(item.get("themes", []) or [])
    selected = _choose_positive_theme(themes) if positive else _choose_negative_theme(themes)
    if selected:
        return selected
    return CATEGORY_DISPLAY.get(str(item.get("aspect", "")), "핵심 경험")


def _strength_experience_summary(*, aspect: str, theme: str) -> str:
    if aspect == "gameplay":
        return "전투 리듬이 손에 붙기 시작하면 몰입이 빠르게 올라 한 판 더 하게 되는 흐름이 만들어집니다."
    if aspect == "story":
        return "진행할수록 스토리 몰입이 깊어져 다음 구간을 계속 확인하고 싶어지는 타입입니다."
    if aspect == "graphics":
        return "월드 연출과 분위기 체감이 좋아 감상형 플레이 만족도가 높게 유지됩니다."
    if aspect == "customization":
        return "커스터마이징 과정 자체가 재미 요소로 작동해 플레이 동기를 유지하기 쉽습니다."
    if aspect == "content_depth":
        return "중장기 플레이에서도 파고들 목표가 남아 있어 플레이 지속성이 높은 편입니다."
    if aspect in {"difficulty", "difficulty_onboarding"}:
        return "처음에는 난도가 높게 느껴질 수 있지만, 적응 이후 성취 체감이 크게 돌아오는 편입니다."
    return "플레이를 이어갈수록 장점 체감이 커져 전반 만족도로 이어지는 흐름입니다."


def _risk_experience_summary(*, aspect: str, theme: str) -> str:
    if aspect == "performance":
        return "교전이나 이동 중 성능 변동이 발생하면 몰입이 갑자기 끊길 수 있습니다."
    if aspect == "bugs":
        return "진행 중 오류가 발생하면 플레이 리듬이 자주 끊겨 피로가 누적될 수 있습니다."
    if aspect in {"difficulty", "difficulty_onboarding"}:
        return "초반 규칙 적응에 실패하면 이탈 가능성이 빠르게 커질 수 있습니다."
    if aspect == "monetization":
        return "비용 대비 만족 기준이 높은 플레이어에게는 체감 만족이 낮아질 가능성이 있습니다."
    return "일부 구간에서 피로가 누적될 수 있어 시작 전 감수 범위를 확인하는 편이 안전합니다."


def _build_evidence_blocks(consensus_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build insight+evidence blocks from high-consensus repeated opinions."""
    aspects = list(consensus_payload.get("consensus_aspects", []) or [])
    thresholds = consensus_payload.get("consensus_thresholds", {}) or {}
    high_min = int(thresholds.get("high_min_mentions", 12))
    medium_min = int(thresholds.get("medium_min_mentions", 6))
    high_items = [item for item in aspects if item.get("consensus_level") == "high"]
    min_mentions = high_min
    if not high_items:
        high_items = [item for item in aspects if item.get("consensus_level") == "medium"]
        min_mentions = medium_min
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
                "full_texts": [],
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
            full_text = " ".join(
                str(snippet.get("full_text") or snippet.get("snippet", "")).split()
            ).strip()
            if not text or text in bucket["snippets"]:
                continue
            if not _snippet_matches_stance(text, stance):
                continue
            if match_tokens and not _snippet_matches_theme(text, match_tokens):
                continue
            bucket["snippets"].append(text)
            bucket["full_texts"].append(full_text or text)
            if len(bucket["snippets"]) >= 4:
                break

        # Relax slightly when strict theme match is too narrow.
        if len(bucket["snippets"]) < 2:
            relaxed_pool: list[tuple[int, str]] = []
            for snippet in stance_snippets:
                text = _prepare_evidence_source_text(str(snippet.get("snippet", "")), limit=1200)
                if not text or text in bucket["snippets"]:
                    continue
                if _is_noisy_evidence_text(text):
                    continue
                if not _snippet_matches_stance(text, stance):
                    continue
                relaxed_pool.append((_snippet_theme_overlap_score(text, match_tokens), text))
            relaxed_pool.sort(key=lambda item: item[0], reverse=True)
            for _, text in relaxed_pool:
                bucket["snippets"].append(text)
                bucket["full_texts"].append(text)
                if len(bucket["snippets"]) >= 3:
                    break

    blocks: list[dict[str, Any]] = []
    for bucket in sorted(grouped.values(), key=lambda b: (-int(b["mention_count"]), b["theme"])):
        if int(bucket["mention_count"]) < min_mentions:
            continue
        if len(bucket["snippets"]) < 2:
            continue

        title = _build_block_title(
            bucket["theme"],
            bucket["stance"],
            aspects=list(bucket.get("aspects", []) or []),
        )
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
                "evidence_full_text": (bucket["full_texts"][:3] or bucket["snippets"][:3]),
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


def _build_block_title(theme: str, stance: str, *, aspects: list[str] | None = None) -> str:
    primary_aspect = str((aspects or [""])[0] or "")
    if stance == "positive":
        return _strength_outcome_title(aspect=primary_aspect or "gameplay")
    return _risk_outcome_title(aspect=primary_aspect or "performance")


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


def _snippet_theme_overlap_score(text: str, theme_tokens: list[str]) -> int:
    if not theme_tokens:
        return 0
    normalized = str(text).lower().replace(" ", "")
    return sum(1 for token in theme_tokens if token.replace(" ", "") in normalized)


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
    """Compress grouped evidence snippets (stage 3)."""
    strengths = list(evidence_sections.get("strengths", []) or [])
    risks = list(evidence_sections.get("risks", []) or [])
    if not strengths and not risks:
        return {"strengths": [], "risks": []}

    compressor = (
        OpenAIEvidenceSnippetCompressor()
        if use_llm and _should_use_llm_evidence_compression()
        else None
    )
    llm_enabled = bool(compressor and compressor.available)

    def _compress_block_list(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compressed_blocks: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            snippets = block.get("evidence_snippets")
            if not isinstance(snippets, list):
                continue
            full_texts = block.get("evidence_full_text")
            if not isinstance(full_texts, list):
                full_texts = list(snippets)
            pair_count = min(len(snippets), len(full_texts))
            if pair_count < 2:
                continue
            snippets = [str(item) for item in list(snippets[:pair_count]) if str(item)]
            full_texts = [str(item) for item in list(full_texts[:pair_count]) if str(item)]
            pair_count = min(len(snippets), len(full_texts))
            if pair_count < 2:
                continue
            snippets = snippets[:pair_count]
            full_texts = full_texts[:pair_count]
            stance = str(block.get("stance", "mixed"))
            match_tokens = _build_theme_match_tokens(
                str(block.get("theme", "")),
                [str(item) for item in list(block.get("aspect_keys", []) or [])],
            )

            strict_hits: list[tuple[str, str]] = []
            relaxed_hits: list[tuple[str, str]] = []
            seen: set[str] = set()
            for idx, raw in enumerate(snippets):
                raw_text = str(raw or "").strip()
                raw_full_text = " ".join(str(full_texts[idx] if idx < len(full_texts) else raw_text).split()).strip()
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
                if _is_noisy_evidence_text(normalized):
                    continue
                if not _snippet_matches_stance(normalized, stance):
                    continue

                if normalized not in seen:
                    seen.add(normalized)
                    full_value = raw_full_text or raw_text
                    if match_tokens and _snippet_matches_theme(normalized, match_tokens):
                        strict_hits.append((normalized, full_value))
                    else:
                        relaxed_hits.append((normalized, full_value))

            rewritten = list(strict_hits)
            if len(rewritten) < 2:
                for candidate in relaxed_hits:
                    if candidate in rewritten:
                        continue
                    rewritten.append(candidate)
                    if len(rewritten) >= 3:
                        break

            if len(rewritten) < 2:
                continue
            next_block = dict(block)
            next_block["evidence_snippets"] = [item[0] for item in rewritten[:3]]
            next_block["evidence_full_text"] = [item[1] for item in rewritten[:3]]
            compressed_blocks.append(next_block)
        return compressed_blocks

    return {
        "strengths": _compress_block_list(strengths)[:3],
        "risks": _compress_block_list(risks)[:3],
    }


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


def _apply_evidence_relevance_judge(
    *,
    evidence_sections: dict[str, list[dict[str, Any]]],
    consensus_payload: dict[str, Any],
    use_llm: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Optional LLM judge hook for evidence relevance (default OFF)."""
    if not use_llm or not _should_use_llm_evidence_judge():
        return evidence_sections

    judge = OpenAIEvidenceRelevanceJudge()
    if not judge.available:
        return evidence_sections

    max_calls_per_block = max(2, int(os.getenv("EVIDENCE_JUDGE_MAX_PER_BLOCK", "8")))
    max_calls_total = max(4, int(os.getenv("EVIDENCE_JUDGE_MAX_TOTAL", "32")))
    min_confidence = min(1.0, max(0.0, float(os.getenv("EVIDENCE_JUDGE_MIN_CONFIDENCE", "0.65"))))
    timeout_seconds = max(3, int(os.getenv("EVIDENCE_JUDGE_TIMEOUT_SECONDS", "8")))
    retry_limit = max(0, int(os.getenv("EVIDENCE_JUDGE_RETRY_LIMIT", "1")))

    remaining_calls = max_calls_total

    def _refine_block_list(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal remaining_calls
        refined: list[dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            snippets = [str(item) for item in list(block.get("evidence_snippets", []) or []) if str(item)]
            full_texts = [str(item) for item in list(block.get("evidence_full_text", []) or []) if str(item)]
            if not full_texts:
                full_texts = list(snippets)
            pair_count = min(len(snippets), len(full_texts))
            if pair_count < 2:
                refined.append(dict(block))
                continue
            snippets = snippets[:pair_count]
            full_texts = full_texts[:pair_count]

            stance = str(block.get("stance", "mixed"))
            theme = str(block.get("theme", "")).strip() or str(block.get("title", "")).strip()
            block_title = str(block.get("title", "핵심 근거"))

            accepted: list[tuple[float, str, str]] = []
            rejected: list[tuple[str, str]] = []
            local_calls = 0

            for idx, snippet in enumerate(snippets):
                full_value = full_texts[idx] if idx < len(full_texts) else snippet
                if remaining_calls <= 0 or local_calls >= max_calls_per_block:
                    rejected.append((snippet, full_value))
                    continue
                judged = judge.judge(
                    expected_stance=stance,
                    expected_theme=theme,
                    block_title=block_title,
                    snippet=snippet,
                    timeout_seconds=timeout_seconds,
                    retry_limit=retry_limit,
                )
                remaining_calls -= 1
                local_calls += 1
                if judged and judged.fit and judged.stance_match and judged.confidence >= min_confidence:
                    accepted.append((judged.confidence, snippet, full_value))
                else:
                    rejected.append((snippet, full_value))

            accepted.sort(key=lambda item: item[0], reverse=True)
            selected: list[tuple[str, str]] = [(snippet, full_value) for _, snippet, full_value in accepted]

            for snippet, full_value in rejected:
                if len(selected) >= 3:
                    break
                selected.append((snippet, full_value))

            if len(selected) < 2:
                match_tokens = _build_theme_match_tokens(
                    theme,
                    [str(item) for item in list(block.get("aspect_keys", []) or []) if str(item)],
                )
                recovered = _select_relaxed_evidence_snippets(
                    consensus_payload=consensus_payload,
                    stance=stance,
                    match_tokens=match_tokens,
                    minimum=2,
                    maximum=3,
                )
                seen = {snippet for snippet, _ in selected}
                for snippet in recovered:
                    if snippet in seen:
                        continue
                    selected.append((snippet, snippet))
                    seen.add(snippet)
                    if len(selected) >= 3:
                        break

            if len(selected) < 2:
                selected = list(zip(snippets[:3], full_texts[:3], strict=False))

            next_block = dict(block)
            next_block["evidence_snippets"] = [snippet for snippet, _ in selected[:3]]
            next_block["evidence_full_text"] = [full_value for _, full_value in selected[:3]]
            refined.append(next_block)
        return refined

    return {
        "strengths": _refine_block_list(list(evidence_sections.get("strengths", []) or [])),
        "risks": _refine_block_list(list(evidence_sections.get("risks", []) or [])),
    }


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
    if len(result) > 260:
        result = _prepare_evidence_source_text(result, limit=260)
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
        full_texts = item.get("evidence_full_text")
        if full_texts is not None:
            if not isinstance(full_texts, list):
                return False
            if len(full_texts) != len(snippets):
                return False
            if any(not isinstance(text, str) for text in full_texts):
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
