export function toList(values) {
  return Array.isArray(values) ? values : [];
}

export function recommendationLabel(value) {
  const labels = {
    buy_now: "지금 구매 추천",
    buy_on_sale: "할인 구매 추천",
    wait: "업데이트 관망 추천",
    not_recommended: "현재 비추천",
    free_play_recommended: "무료 플레이 추천",
    play_now: "지금 플레이 추천",
    try_lightly: "가볍게 시작해보기 좋음",
  };
  return labels[value] || "-";
}

export function recentStateLabel(value) {
  const labels = {
    improving: "개선 중",
    stable: "안정",
    declining: "악화 중",
    mixed: "혼재",
    insufficient_data: "판단 보류",
  };
  return labels[value] || "-";
}

export function buyBadgeClass(value) {
  const map = {
    buy_now: "buy-now",
    buy_on_sale: "buy-sale",
    wait: "buy-wait",
    not_recommended: "buy-avoid",
    free_play_recommended: "buy-free",
    play_now: "buy-free",
    try_lightly: "buy-try",
  };
  return map[value] || "neutral";
}

function normalizeSnippetText(value) {
  return String(value || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t\f\v]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitSnippetSentences(text) {
  return String(text || "")
    .replace(/\n+/g, " ")
    .split(/(?<=[.!?。！？])\s+/u)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function formatSnippetForDisplay(snippet) {
  const normalized = normalizeSnippetText(snippet);
  if (!normalized) {
    return "";
  }

  const sentences = splitSnippetSentences(normalized);
  if (sentences.length <= 1) {
    return normalized;
  }

  const lines = [];
  for (let index = 0; index < sentences.length; index += 2) {
    lines.push(sentences.slice(index, index + 2).join(" ").trim());
  }
  return lines.join("\n");
}

function normalizeEvidenceBlock(block) {
  if (!block || typeof block !== "object") {
    return null;
  }

  const title = String(block.title || "").trim().replace(/\s+/g, " ");
  const whyItMatters = String(block.why_it_matters || block.explanation || "")
    .trim()
    .replace(/\s+/g, " ");
  const snippets = toList(block.evidence_snippets)
    .map((snippet) => normalizeSnippetText(snippet))
    .filter(Boolean)
    .slice(0, 3);

  if (!title || !whyItMatters || snippets.length < 2) {
    return null;
  }

  return {
    title,
    whyItMatters,
    evidenceSnippets: snippets,
  };
}

export function normalizeEvidenceSections(report) {
  const sections = report && typeof report === "object" ? report.evidence_sections : null;
  if (!sections || typeof sections !== "object") {
    return { loved: [], complained: [] };
  }

  const strengths = Array.isArray(sections.strengths) ? sections.strengths : [];
  const risks = Array.isArray(sections.risks) ? sections.risks : [];
  return {
    loved: strengths.map(normalizeEvidenceBlock).filter(Boolean).slice(0, 3),
    complained: risks.map(normalizeEvidenceBlock).filter(Boolean).slice(0, 3),
  };
}

export function formatGeneratedAt(generatedAt) {
  if (!generatedAt) {
    return "업데이트 정보 없음";
  }
  return `업데이트: ${new Date(generatedAt).toLocaleString("ko-KR")}`;
}
