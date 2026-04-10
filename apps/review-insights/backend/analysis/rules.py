"""Deterministic preprocessing rules for Korean Steam reviews."""

from __future__ import annotations

import re

HANGUL_PATTERN = re.compile(r"[가-힣]")
VISIBLE_CHAR_PATTERN = re.compile(r"[A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ]")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣]+")
REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{3,}")
WHITESPACE_PATTERN = re.compile(r"\s+")

LOW_QUALITY_TEXTS = {
    "",
    ".",
    "..",
    "...",
    "ㅋㅋ",
    "ㅋㅋㅋ",
    "ㅋㅋㅋㅋ",
    "ㅎㅎ",
    "ㅎㅎㅎ",
    "ㅜㅜ",
    "ㅠㅠ",
    "굿",
    "good",
    "bad",
}

PROFANITY_TOKENS = {
    "쓰레기",
    "개쓰레기",
    "병신",
    "좆같다",
    "ㅈ같다",
    "씨발",
    "시발",
    "ㅅㅂ",
    "망겜",
    "개망",
    "노답",
}

NOISE_TOKENS = {
    "ㅋㅋ",
    "ㅋㅋㅋ",
    "ㅎㅎ",
    "ㅎㅎㅎ",
    "ㅠㅠ",
    "ㅜㅜ",
    "진짜",
    "너무",
    "그냥",
    "완전",
}

TOPIC_HINT_TOKENS = {
    "버그",
    "튕김",
    "충돌",
    "에러",
    "프레임",
    "렉",
    "최적화",
    "매칭",
    "서버",
    "과금",
    "조작",
    "번역",
    "스토리",
    "밸런스",
    "난이도",
    "그래픽",
    "아트",
}

POSITIVE_HINT_TOKENS = {
    "재밌",
    "좋",
    "훌륭",
    "추천",
    "만족",
    "깔끔",
}

NEGATIVE_HINT_TOKENS = {
    "별로",
    "나쁘",
    "불편",
    "아쉽",
    "문제",
    "심함",
    "답답",
    "느림",
    "떨어짐",
}

FIGURATIVE_HINT_TOKENS = {
    "천국",
    "지옥",
    "미쳤",
    "살인적",
}


def normalize_text(text: str) -> str:
    """Normalize whitespace and repeated punctuation without rewriting the review."""
    normalized = WHITESPACE_PATTERN.sub(" ", text or "").strip()
    normalized = REPEATED_CHAR_PATTERN.sub(r"\1\1", normalized)
    return normalized


def _visible_chars(text: str) -> list[str]:
    return VISIBLE_CHAR_PATTERN.findall(text)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def calculate_hangul_ratio(text: str) -> float:
    """Return the ratio of Hangul characters among visible characters."""
    visible_chars = _visible_chars(text)
    if not visible_chars:
        return 0.0

    hangul_count = len(HANGUL_PATTERN.findall("".join(visible_chars)))
    return hangul_count / len(visible_chars)


def is_low_quality_review(text: str) -> bool:
    """Conservatively exclude reviews that contain almost no meaningful information."""
    normalized = normalize_text(text).lower()
    condensed = normalized.replace(" ", "")

    if condensed in LOW_QUALITY_TEXTS:
        return True

    if len(_visible_chars(normalized)) <= 3:
        return True

    if len(set(condensed)) == 1 and len(condensed) >= 3:
        return True

    tokens = tokenize(normalized)
    if not tokens:
        return True

    meaningful_tokens = [
        token
        for token in tokens
        if token not in NOISE_TOKENS and len(token) >= 2
    ]
    return len(meaningful_tokens) == 0


def is_profanity_only_review(text: str) -> bool:
    """Return True only when profanity exists without meaningful topic feedback."""
    tokens = tokenize(normalize_text(text))
    if not tokens:
        return False

    contains_profanity = any(token in PROFANITY_TOKENS for token in tokens)
    if not contains_profanity:
        return False

    remaining_tokens = [
        token
        for token in tokens
        if token not in PROFANITY_TOKENS and token not in NOISE_TOKENS
    ]
    if not remaining_tokens:
        return True

    has_topic_hint = any(
        token in TOPIC_HINT_TOKENS or len(token) >= 3 for token in remaining_tokens
    )
    return not has_topic_hint


def detect_ambiguity_flags(
    text: str,
    hangul_ratio: float,
    is_low_quality: bool,
    is_profanity_only: bool,
) -> list[str]:
    """Flag reviews that may need a later LLM fallback decision."""
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    flags: list[str] = []

    if 0.20 <= hangul_ratio < 0.50:
        flags.append("ambiguous_language")

    has_profanity = any(token in PROFANITY_TOKENS for token in tokens)
    if has_profanity and not is_profanity_only:
        flags.append("ambiguous_profanity")

    has_positive = any(any(hint in token for hint in POSITIVE_HINT_TOKENS) for token in tokens)
    has_negative = any(any(hint in token for hint in NEGATIVE_HINT_TOKENS) for token in tokens)
    if has_positive and has_negative:
        flags.append("ambiguous_sentiment")

    if any(any(hint in token for hint in FIGURATIVE_HINT_TOKENS) for token in tokens):
        flags.append("figurative_expression_detected")

    topic_hits = sum(1 for token in tokens if token in TOPIC_HINT_TOKENS)
    if topic_hits >= 3:
        flags.append("ambiguous_category")

    if is_low_quality and len(tokens) >= 3:
        flags.append("ambiguous_quality")

    return flags
