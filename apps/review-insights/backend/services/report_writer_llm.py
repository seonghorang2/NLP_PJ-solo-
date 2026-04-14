"""LLM writer for consensus-driven purchase decision reports."""

from __future__ import annotations

import json
import os
from typing import Any

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

SYSTEM_PROMPT = """
You are writing a Korean purchase-decision report for one Steam game.

This is NOT an internal dashboard summary.
This is a consumer decision report.

Primary goal:
- Help users decide one of: buy_now, buy_on_sale, wait, not_recommended

Critical rules:
1) Consensus first
- High-consensus aspects are primary.
- Medium-consensus aspects are secondary support.
- Low-consensus aspects must not become main points.
- Do not let one dramatic review dominate.

2) Grounding
- Use only information provided in input JSON.
- Strengths and risks must be supported by repeated evidence.
- Do not invent facts, features, trends, or player opinions.

3) Writing quality
- Avoid generic filler phrases.
- Keep sentences concise and specific.
- Vary sentence openings and rhythm naturally.
- Make the text feel like it came from reading many reviews.

4) Output contract
- Return valid JSON only.
- Required keys:
  headline, buy_recommendation, buy_timing_summary, good_for, not_good_for,
  top_strengths, top_risks, recent_state, evidence_reviews
- buy_recommendation must be one of:
  buy_now, buy_on_sale, wait, not_recommended
- recent_state must contain: status, summary
""".strip()


class OpenAIReportWriter:
    """Generate consumer-facing report text from consensus payload."""

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

    @property
    def available(self) -> bool:
        return self._client is not None

    def generate_report(
        self,
        consensus_payload: dict[str, Any],
        *,
        timeout_seconds: int = 30,
        retry_limit: int = 1,
    ) -> dict[str, Any] | None:
        """Return report JSON or None on failure/invalid output."""
        if self._client is None:
            return None

        user_prompt = (
            "아래 JSON을 기반으로 한국어 구매 판단 리포트를 생성하세요.\n"
            "고합의 신호를 우선하고, 저빈도 의견은 메인에서 제외하세요.\n"
            "출력은 반드시 JSON만 반환하세요.\n\n"
            f"{json.dumps(consensus_payload, ensure_ascii=False)}"
        )

        for _ in range(retry_limit + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.35,
                    response_format={"type": "json_object"},
                    timeout=timeout_seconds,
                )
                content = response.choices[0].message.content if response.choices else None
                if not content:
                    continue
                payload = json.loads(content)
                if _validate_report_payload(payload):
                    return payload
            except Exception:
                continue
        return None


def _validate_report_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False

    required = {
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
    if not required.issubset(set(payload.keys())):
        return False

    if payload.get("buy_recommendation") not in {
        "buy_now",
        "buy_on_sale",
        "wait",
        "not_recommended",
    }:
        return False

    if not isinstance(payload.get("good_for"), list):
        return False
    if not isinstance(payload.get("not_good_for"), list):
        return False
    if not isinstance(payload.get("top_strengths"), list):
        return False
    if not isinstance(payload.get("top_risks"), list):
        return False
    if not isinstance(payload.get("evidence_reviews"), list):
        return False

    recent_state = payload.get("recent_state")
    if not isinstance(recent_state, dict):
        return False
    if "status" not in recent_state or "summary" not in recent_state:
        return False
    return True

