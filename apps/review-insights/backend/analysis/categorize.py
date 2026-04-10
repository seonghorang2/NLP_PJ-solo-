"""Rule-based multi-label categorization for Korean Steam reviews."""

from __future__ import annotations

from analysis.rules import normalize_text

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "bugs": (
        "버그",
        "튕김",
        "튕기",
        "충돌",
        "에러",
        "크래시",
        "저장 안",
        "저장이 안",
        "세이브",
        "먹통",
    ),
    "performance": (
        "최적화",
        "프레임",
        "프레임드랍",
        "렉",
        "버벅",
        "끊김",
        "발열",
        "로딩",
    ),
    "balance": (
        "밸런스",
        "불균형",
        "사기",
        "너프",
        "버프",
        "op",
    ),
    "story": (
        "스토리",
        "서사",
        "시나리오",
        "연출",
        "캐릭터",
        "대사",
    ),
    "graphics": (
        "그래픽",
        "아트",
        "비주얼",
        "모델링",
        "연출",
    ),
    "monetization": (
        "과금",
        "현질",
        "bm",
        "dlc",
        "확률",
        "패스",
    ),
    "multiplayer": (
        "매칭",
        "서버",
        "큐",
        "멀티",
        "파티",
        "핑",
        "협동",
    ),
    "localization": (
        "번역",
        "오역",
        "자막",
        "현지화",
        "한글화",
    ),
    "difficulty": (
        "난이도",
        "불친절",
        "온보딩",
        "튜토리얼",
        "초반",
    ),
    "controls": (
        "조작",
        "조작감",
        "키마",
        "패드",
        "입력",
        "키배치",
        "반응속도",
    ),
}


def normalize_for_category_match(text: str) -> str:
    """Normalize review text for simple substring matching."""
    return normalize_text(text).lower().replace(" ", "")


def extract_category_tags(text: str) -> list[str]:
    """Return every matched category tag for a review."""
    normalized = normalize_for_category_match(text)
    tags: list[str] = []

    for category, patterns in CATEGORY_PATTERNS.items():
        if any(pattern.lower().replace(" ", "") in normalized for pattern in patterns):
            tags.append(category)

    return tags
