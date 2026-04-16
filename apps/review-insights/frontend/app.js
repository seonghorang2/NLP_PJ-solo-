const form = document.getElementById("report-form");
const gameSelect = document.getElementById("game-select");
const loadButton = document.getElementById("load-button");

const gameName = document.getElementById("game-name");
const buyBadge = document.getElementById("buy-badge");
const headline = document.getElementById("headline");
const buyTimingSummary = document.getElementById("buy-timing-summary");
const recentStateSummary = document.getElementById("recent-state-summary");
const recentStateStatus = document.getElementById("recent-state-status");
const buyRecommendation = document.getElementById("buy-recommendation");
const generatedAt = document.getElementById("generated-at");
const goodForList = document.getElementById("good-for-list");
const notGoodForList = document.getElementById("not-good-for-list");
const strengths = document.getElementById("strengths");
const risks = document.getElementById("risks");
const evidencePositiveList = document.getElementById("evidence-positive-list");
const evidenceNegativeList = document.getElementById("evidence-negative-list");
const evidenceSections = document.querySelector(".evidence-sections");
const evidencePositiveSection = evidencePositiveList?.closest(".evidence-section");
const evidenceNegativeSection = evidenceNegativeList?.closest(".evidence-section");
const disclaimer = document.getElementById("disclaimer");
const statusLine = document.getElementById("status-line");

function setStatus(message) {
  statusLine.textContent = message;
}

function recommendationLabel(value) {
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

function recentStateLabel(value) {
  const labels = {
    improving: "개선 중",
    stable: "안정",
    declining: "악화 중",
    mixed: "혼재",
    insufficient_data: "판단 보류",
  };
  return labels[value] || "-";
}

function buyBadgeClass(value) {
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

function toList(values) {
  return Array.isArray(values) ? values : [];
}

function renderBullets(container, values) {
  container.innerHTML = "";
  const list = toList(values);
  if (list.length === 0) {
    const li = document.createElement("li");
    li.textContent = "데이터가 충분하지 않습니다.";
    container.appendChild(li);
    return;
  }
  list.forEach((value) => {
    const li = document.createElement("li");
    li.textContent = value;
    container.appendChild(li);
  });
}

function renderCards(container, values) {
  container.innerHTML = "";
  const list = toList(values);
  if (list.length === 0) {
    container.innerHTML = '<p class="placeholder">합의 신호가 부족합니다.</p>';
    return;
  }

  list.slice(0, 3).forEach((value) => {
    const card = document.createElement("article");
    card.className = "mini-card";
    card.innerHTML = `
      <h3>${value.title || "-"}</h3>
      <p>${value.summary || "-"}</p>
    `;
    container.appendChild(card);
  });
}

function normalizeEvidenceSections(report) {
  const sections = report && typeof report === "object" ? report.evidence_sections : null;
  if (!sections || typeof sections !== "object") {
    return { loved: [], complained: [] };
  }

  const strengths = Array.isArray(sections.strengths) ? sections.strengths : [];
  const risks = Array.isArray(sections.risks) ? sections.risks : [];
  return {
    loved: strengths
      .map(normalizeEvidenceBlock)
      .filter(Boolean)
      .slice(0, 3),
    complained: risks
      .map(normalizeEvidenceBlock)
      .filter(Boolean)
      .slice(0, 3),
  };
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

function formatSnippetForDisplay(snippet) {
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
    evidence_snippets: snippets,
  };
}

function renderEvidenceSection(container, blocks, emptyMessage) {
  container.innerHTML = "";
  if (blocks.length === 0) {
    const placeholder = document.createElement("p");
    placeholder.className = "placeholder";
    placeholder.textContent = emptyMessage;
    container.appendChild(placeholder);
    return;
  }

  blocks.forEach((block) => {
    const finalSnippets = toList(block.evidence_snippets)
      .map((snippet) => normalizeSnippetText(snippet))
      .filter(Boolean)
      .slice(0, 3);
    const card = document.createElement("article");
    card.className = "evidence-card";

    const title = document.createElement("h3");
    title.textContent = block.title || "-";

    const why = document.createElement("p");
    why.className = "evidence-why";
    why.textContent = block.whyItMatters || "-";

    const list = document.createElement("ul");
    list.className = "evidence-snippets";
    finalSnippets.forEach((snippet) => {
      const li = document.createElement("li");
      li.textContent = formatSnippetForDisplay(snippet);
      list.appendChild(li);
    });

    card.appendChild(title);
    card.appendChild(why);
    card.appendChild(list);
    container.appendChild(card);
  });
}

function renderEvidence(report) {
  const sections = normalizeEvidenceSections(report);
  const positiveCount = sections.loved.length;
  const negativeCount = sections.complained.length;

  if (evidenceSections) {
    const isSparse = positiveCount <= 1 || negativeCount <= 1;
    const hasOnlyOneSide = (positiveCount === 0) !== (negativeCount === 0);
    evidenceSections.classList.toggle("sparse-layout", isSparse);
    evidenceSections.classList.toggle("single-side-layout", hasOnlyOneSide);
  }
  if (evidencePositiveSection) {
    evidencePositiveSection.classList.toggle("is-empty", positiveCount === 0);
    evidencePositiveSection.classList.toggle("is-single", positiveCount === 1);
  }
  if (evidenceNegativeSection) {
    evidenceNegativeSection.classList.toggle("is-empty", negativeCount === 0);
    evidenceNegativeSection.classList.toggle("is-single", negativeCount === 1);
  }

  renderEvidenceSection(
    evidencePositiveList,
    sections.loved,
    "표시할 긍정 근거 리뷰가 없습니다."
  );
  renderEvidenceSection(
    evidenceNegativeList,
    sections.complained,
    "표시할 부정 근거 리뷰가 없습니다."
  );
}

function renderReport(report) {
  const display = report.report_display;
  if (!display || typeof display !== "object") {
    throw new Error("report_display가 없는 리포트입니다.");
  }
  if (
    !report ||
    typeof report !== "object" ||
    !report.evidence_sections ||
    !Array.isArray(report.evidence_sections.strengths) ||
    !Array.isArray(report.evidence_sections.risks)
  ) {
    throw new Error("근거 섹션(강점/리스크)이 없는 리포트입니다.");
  }
  const game = report.game || {};
  const recommendation = display.buy_recommendation || "";
  const recentState = display.recent_state || {};

  gameName.textContent = game.name || `appid ${report.appid}`;
  headline.textContent = display.headline || "-";

  buyBadge.textContent = recommendationLabel(recommendation);
  buyBadge.className = `buy-badge ${buyBadgeClass(recommendation)}`;

  buyTimingSummary.textContent = display.buy_timing_summary || "-";
  recentStateSummary.textContent = recentState.summary || "-";
  recentStateStatus.textContent = `상태: ${recentStateLabel(recentState.status)}`;
  buyRecommendation.textContent = recommendationLabel(recommendation);
  generatedAt.textContent = report.generated_at
    ? `업데이트: ${new Date(report.generated_at).toLocaleString("ko-KR")}`
    : "업데이트 정보 없음";

  renderBullets(goodForList, display.good_for);
  renderBullets(notGoodForList, display.not_good_for);
  renderCards(strengths, display.top_strengths);
  renderCards(risks, display.top_risks);

  renderEvidence(report);
  disclaimer.textContent = report.disclaimer || "";
}

async function loadJson(url, fallbackMessage) {
  const response = await fetch(url);
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.detail || fallbackMessage);
  }
  return response.json();
}

async function loadDemoGames() {
  const payload = await loadJson("/api/games", "게임 목록을 불러오지 못했습니다.");
  const games = toList(payload.games).filter((item) => item.report_ready);

  gameSelect.innerHTML = "";
  if (games.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "준비된 리포트가 없습니다.";
    gameSelect.appendChild(option);
    return null;
  }

  games.forEach((game, index) => {
    const option = document.createElement("option");
    option.value = String(game.appid);
    option.textContent = `${game.name} (${game.appid})`;
    if (index === 0) {
      option.selected = true;
    }
    gameSelect.appendChild(option);
  });

  return Number(gameSelect.value);
}

async function loadReport(appid) {
  return loadJson(`/api/games/${appid}/report`, "리포트를 불러오지 못했습니다.");
}

async function openReport(appid) {
  if (!appid) {
    setStatus("리포트 대상 게임을 선택해 주세요.");
    return;
  }

  loadButton.disabled = true;
  setStatus("구매 판단 리포트를 불러오는 중입니다...");
  try {
    const report = await loadReport(appid);
    renderReport(report);
    setStatus("불러오기 완료");
  } catch (error) {
    setStatus(error.message || "리포트 로드에 실패했습니다.");
  } finally {
    loadButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await openReport(Number(gameSelect.value));
});

async function bootstrap() {
  setStatus("게임 목록 준비 중...");
  try {
    const firstAppid = await loadDemoGames();
    if (firstAppid) {
      await openReport(firstAppid);
      return;
    }
    setStatus("표시 가능한 게임이 없습니다.");
  } catch (error) {
    setStatus(error.message || "초기화에 실패했습니다.");
  }
}

bootstrap();
