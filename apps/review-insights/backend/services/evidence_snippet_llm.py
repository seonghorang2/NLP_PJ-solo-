"""LLM-based evidence snippet compressor."""

from __future__ import annotations

import json
import os
import re
from typing import Any

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


SYSTEM_PROMPT = """
너는 스팀 리뷰 근거 문장을 읽기 쉬운 핵심 스니펫으로 재작성하는 편집기다.

목표:
- 원문 의미와 감정 톤을 유지한 채, 읽기 쉬운 짧은 근거 문장으로 압축한다.

규칙:
1) 출력은 한국어 문장 1~4개
2) 반드시 포함:
   - 무엇이 일어났는지(경험)
   - 유저가 어떻게 느꼈는지(반응)
3) 문장을 중간에 자르지 말 것
4) 과도한 축약, 과장, 사실 추가 금지
5) 일반론/상투어 금지 ("일부 유저는" 같은 표현 금지)
6) 실제 유저가 말한 듯 자연스럽게 작성

출력:
- JSON only
- {"snippet": "<재작성된 1~4문장>"}
""".strip()


class OpenAIEvidenceSnippetCompressor:
    """Compress one evidence review snippet into readable 1~4 sentences."""

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
        self._cache: dict[str, str | None] = {}

    @property
    def available(self) -> bool:
        return self._client is not None

    def compress(
        self,
        *,
        raw_text: str,
        stance: str,
        context_title: str,
        timeout_seconds: int = 15,
        retry_limit: int = 1,
    ) -> str | None:
        """Return compressed snippet or None when unavailable/invalid."""
        normalized = " ".join((raw_text or "").split())
        if not normalized:
            return None

        cache_key = f"{stance}|{context_title}|{normalized}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._client is None:
            self._cache[cache_key] = None
            return None

        user_prompt = (
            "다음 리뷰를 근거 스니펫으로 재작성하세요.\n"
            f"- 맥락: {context_title}\n"
            f"- 성격: {stance}\n"
            "- 반드시 1~4문장\n"
            "- JSON만 반환\n\n"
            f"원문:\n{normalized}"
        )

        result: str | None = None
        for _ in range(retry_limit + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    timeout=timeout_seconds,
                )
                content = response.choices[0].message.content if response.choices else None
                if not content:
                    continue
                payload = json.loads(content)
                candidate = _validate_snippet_payload(payload)
                if candidate is not None:
                    result = candidate
                    break
            except Exception:
                continue

        self._cache[cache_key] = result
        return result


def _validate_snippet_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    snippet = payload.get("snippet")
    if not isinstance(snippet, str):
        return None

    normalized = " ".join(snippet.split())
    if not normalized:
        return None

    sentence_count = _count_sentences(normalized)
    if sentence_count < 1 or sentence_count > 4:
        return None
    if len(normalized) > 420:
        return None
    if normalized.endswith("...") or normalized.endswith("…"):
        return None
    return normalized


def _count_sentences(text: str) -> int:
    parts = [
        part.strip()
        for part in re.split(r"[.!?\u3002\uff01\uff1f]+", text)
        if part.strip()
    ]
    return len(parts)

