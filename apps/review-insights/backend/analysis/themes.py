"""Theme extraction helpers for categorized Korean Steam reviews."""

from __future__ import annotations

from collections import Counter

from models.schemas import ProcessedReview

THEME_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "bugs": {
        "충돌 및 튕김": ("튕김", "튕기", "충돌", "크래시"),
        "저장 문제": ("저장 안", "저장이 안", "세이브"),
        "일반 버그": ("버그", "에러", "먹통"),
    },
    "performance": {
        "최적화 문제": ("최적화", "프레임", "프레임드랍", "렉", "버벅", "끊김"),
        "로딩 지연": ("로딩",),
        "발열 문제": ("발열",),
    },
    "balance": {
        "밸런스 불만": ("밸런스", "불균형", "사기", "너프", "버프", "op"),
    },
    "story": {
        "스토리 몰입": ("스토리", "서사", "시나리오"),
        "캐릭터 및 연출": ("캐릭터", "대사", "연출"),
    },
    "graphics": {
        "그래픽 품질": ("그래픽", "비주얼", "모델링"),
        "아트 스타일": ("아트",),
    },
    "monetization": {
        "과금 부담": ("과금", "현질", "bm", "확률"),
        "DLC 정책": ("dlc", "패스"),
    },
    "multiplayer": {
        "매칭 지연": ("매칭", "큐"),
        "서버 불안정": ("서버", "핑"),
        "멀티플레이 경험": ("멀티", "파티", "협동"),
    },
    "localization": {
        "번역 품질": ("번역", "오역", "자막", "현지화", "한글화"),
    },
    "difficulty": {
        "난이도 문제": ("난이도",),
        "온보딩 불친절": ("불친절", "온보딩", "튜토리얼", "초반"),
    },
    "controls": {
        "조작감 문제": ("조작", "조작감", "입력", "반응속도"),
        "입력 장치 문제": ("키마", "패드", "키배치"),
    },
}

STOPWORDS = {
    "그리고",
    "하지만",
    "그래서",
    "그냥",
    "너무",
    "진짜",
    "정말",
    "조금",
    "에서",
    "같음",
    "같다",
    "좋은데",
    "별로라",
    "느림",
}


def _match_canonical_theme(category: str, normalized_text: str) -> str | None:
    patterns = THEME_PATTERNS.get(category, {})
    for canonical_theme, aliases in patterns.items():
        if any(alias.replace(" ", "") in normalized_text for alias in aliases):
            return canonical_theme
    return None


def extract_review_themes(processed_review: ProcessedReview) -> dict[str, str]:
    """Return one canonical theme per matched category for a review."""
    normalized = processed_review.normalized_text.lower().replace(" ", "")
    themes: dict[str, str] = {}

    for category in processed_review.category_tags:
        canonical_theme = _match_canonical_theme(category, normalized)
        if canonical_theme is not None:
            themes[category] = canonical_theme

    return themes


def extract_keywords(text: str) -> list[str]:
    """Extract simple keyword candidates from normalized Korean review text."""
    words = [word.strip(".,!?") for word in text.split()]
    keywords: list[str] = []

    for word in words:
        clean = word.lower()
        if len(clean) < 2:
            continue
        if clean in STOPWORDS:
            continue
        keywords.append(clean)

    return keywords


def collect_top_keywords(processed_reviews: list[ProcessedReview], limit: int = 5) -> list[str]:
    """Aggregate the most frequent keyword candidates across reviews."""
    counter: Counter[str] = Counter()

    for review in processed_reviews:
        if not review.included_in_analysis:
            continue
        counter.update(extract_keywords(review.normalized_text))

    return [keyword for keyword, _count in counter.most_common(limit)]


def collect_top_themes(
    processed_reviews: list[ProcessedReview],
    category: str,
    limit: int = 3,
) -> list[str]:
    """Aggregate the most common canonical themes for a given category."""
    counter: Counter[str] = Counter()

    for review in processed_reviews:
        if not review.included_in_analysis or category not in review.category_tags:
            continue

        theme = extract_review_themes(review).get(category)
        if theme is not None:
            counter[theme] += 1

    return [theme for theme, _count in counter.most_common(limit)]
