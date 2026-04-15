"""LLM judge for evidence relevance (stance/theme fit)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


SYSTEM_PROMPT = """
You evaluate whether a review snippet fits an evidence block.

Rules:
- Grounding: use only provided text.
- Judge only fit quality, do not rewrite.
- Prioritize stance match first, then theme relevance.
- JSON only.

Return:
{
  "fit": true|false,
  "stance_match": true|false,
  "theme_match": true|false,
  "confidence": 0.0~1.0,
  "reason": "short string"
}
""".strip()


@dataclass(slots=True)
class EvidenceJudgeResult:
    fit: bool
    stance_match: bool
    theme_match: bool
    confidence: float
    reason: str


class OpenAIEvidenceRelevanceJudge:
    """Judge evidence snippet relevance with small-call budget."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = (
            OpenAI(api_key=self.api_key)
            if OpenAI is not None and self.api_key
            else None
        )
        self._cache: dict[str, EvidenceJudgeResult | None] = {}

    @property
    def available(self) -> bool:
        return self._client is not None

    def judge(
        self,
        *,
        expected_stance: str,
        expected_theme: str,
        block_title: str,
        snippet: str,
        timeout_seconds: int = 8,
        retry_limit: int = 1,
    ) -> EvidenceJudgeResult | None:
        text = " ".join((snippet or "").split()).strip()
        if not text:
            return None
        cache_key = (
            f"{expected_stance}|{expected_theme}|{block_title}|{text}"
        ).lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._client is None:
            self._cache[cache_key] = None
            return None

        payload = {
            "expected_stance": expected_stance,
            "expected_theme": expected_theme,
            "block_title": block_title,
            "snippet": text,
        }
        prompt = (
            "Evaluate fit for buyer-facing evidence block.\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        result: EvidenceJudgeResult | None = None
        for _ in range(retry_limit + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    timeout=timeout_seconds,
                )
                content = response.choices[0].message.content if response.choices else None
                if not content:
                    continue
                parsed = json.loads(content)
                validated = _validate_result(parsed)
                if validated is not None:
                    result = validated
                    break
            except Exception:
                continue

        self._cache[cache_key] = result
        return result


def _validate_result(value: Any) -> EvidenceJudgeResult | None:
    if not isinstance(value, dict):
        return None
    fit = value.get("fit")
    stance_match = value.get("stance_match")
    theme_match = value.get("theme_match")
    confidence = value.get("confidence")
    reason = value.get("reason")
    if not isinstance(fit, bool):
        return None
    if not isinstance(stance_match, bool):
        return None
    if not isinstance(theme_match, bool):
        return None
    if not isinstance(confidence, (int, float)):
        return None
    if not isinstance(reason, str):
        return None
    conf = max(0.0, min(1.0, float(confidence)))
    return EvidenceJudgeResult(
        fit=fit,
        stance_match=stance_match,
        theme_match=theme_match,
        confidence=conf,
        reason=reason.strip(),
    )

