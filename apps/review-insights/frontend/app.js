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
const recentStateLine = document.getElementById("recent-state-line");
const evidencePositiveList = document.getElementById("evidence-positive-list");
const evidenceNegativeList = document.getElementById("evidence-negative-list");
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
  };
  return map[value] || "neutral";
}

function toList(values) {
  return Array.isArray(values) ? values : [];
}

function clampText(value, maxLength) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text) {
    return "";
  }
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1).trim()}…`;
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

function normalizeEvidenceBlocks(values) {
  const list = toList(values);
  if (list.length === 0) {
    return [];
  }

  // New structure: insight+evidence blocks
  if (
    typeof list[0] === "object" &&
    list[0] !== null &&
    Array.isArray(list[0].evidence_snippets)
  ) {
    return list;
  }

  // Backward compatibility: old raw snippet list
  const grouped = new Map();
  list.forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const stance = item.stance === "negative" ? "negative" : "positive";
    const key = `${stance}::${item.aspect_label || item.aspect || "핵심 의견"}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        title: `[${item.aspect_label || item.aspect || "핵심 의견"}] 대표 의견`,
        explanation:
          stance === "negative"
            ? "반복적으로 등장한 불만 의견입니다."
            : "반복적으로 등장한 긍정 의견입니다.",
        stance,
        consensus_level: "medium",
        mention_count: 0,
        evidence_snippets: [],
      });
    }
    const block = grouped.get(key);
    const snippet = String(item.snippet || "").trim();
    if (snippet && !block.evidence_snippets.includes(snippet)) {
      block.evidence_snippets.push(snippet);
    }
    block.mention_count += 1;
  });

  return [...grouped.values()]
    .filter((block) => block.evidence_snippets.length >= 1)
    .map((block) => ({
      ...block,
      evidence_snippets: block.evidence_snippets.slice(0, 3),
    }))
    .slice(0, 4);
}

function normalizeEvidenceSections(report) {
  const sections = report && typeof report === "object" ? report.evidence_sections : null;
  if (
    sections &&
    typeof sections === "object" &&
    Array.isArray(sections.loved) &&
    Array.isArray(sections.complained)
  ) {
    return {
      loved: normalizeEvidenceBlocks(sections.loved)
        .filter((block) => block.stance === "positive")
        .map(normalizeEvidenceBlock)
        .filter(Boolean)
        .slice(0, 3),
      complained: normalizeEvidenceBlocks(sections.complained)
        .filter((block) => block.stance === "negative")
        .map(normalizeEvidenceBlock)
        .filter(Boolean)
        .slice(0, 3),
    };
  }

  const blocks = normalizeEvidenceBlocks(report ? report.evidence_reviews : []);
  return {
    loved: blocks
      .filter((block) => block.stance === "positive")
      .map(normalizeEvidenceBlock)
      .filter(Boolean)
      .slice(0, 3),
    complained: blocks
      .filter((block) => block.stance === "negative")
      .map(normalizeEvidenceBlock)
      .filter(Boolean)
      .slice(0, 3),
  };
}

function normalizeEvidenceBlock(block) {
  if (!block || typeof block !== "object") {
    return null;
  }
  const title = clampText(block.title, 60);
  const explanation = clampText(block.explanation, 150);
  const snippets = toList(block.evidence_snippets)
    .map((snippet) => clampText(snippet, 120))
    .filter(Boolean)
    .slice(0, 2);

  if (!title || !explanation || snippets.length < 2) {
    return null;
  }

  return {
    ...block,
    title,
    explanation,
    evidence_snippets: snippets,
  };
}

function renderEvidenceSection(container, blocks, emptyMessage) {
  container.innerHTML = "";
  if (blocks.length === 0) {
    container.innerHTML = `<p class="placeholder">${emptyMessage}</p>`;
    return;
  }

  blocks.forEach((block) => {
    const snippets = toList(block.evidence_snippets);
    const card = document.createElement("article");
    card.className = "evidence-card";

    const snippetsHtml = snippets.map((snippet) => `<li>"${snippet}"</li>`).join("");

    card.innerHTML = `
      <p class="evidence-meta">${block.consensus_level || "high"} consensus · ${block.mention_count || 0}건</p>
      <h3>${block.title || "-"}</h3>
      <p class="evidence-text">${block.explanation || "-"}</p>
      <ul class="evidence-snippets">${snippetsHtml}</ul>
    `;
    container.appendChild(card);
  });
}

function renderEvidence(report) {
  const sections = normalizeEvidenceSections(report);
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
  const game = report.game || {};
  const recommendation = report.buy_recommendation || "";
  const recentState = report.recent_state || {};

  gameName.textContent = game.name || `appid ${report.appid}`;
  headline.textContent = report.headline || "-";

  buyBadge.textContent = recommendationLabel(recommendation);
  buyBadge.className = `buy-badge ${buyBadgeClass(recommendation)}`;

  buyTimingSummary.textContent = report.buy_timing_summary || "-";
  recentStateSummary.textContent = recentState.summary || "-";
  recentStateStatus.textContent = `상태: ${recentStateLabel(recentState.status)}`;
  buyRecommendation.textContent = recommendationLabel(recommendation);
  generatedAt.textContent = report.generated_at
    ? `업데이트: ${new Date(report.generated_at).toLocaleString("ko-KR")}`
    : "업데이트 정보 없음";

  renderBullets(goodForList, report.good_for);
  renderBullets(notGoodForList, report.not_good_for);
  renderCards(strengths, report.top_strengths);
  renderCards(risks, report.top_risks);

  recentStateLine.textContent = recentState.summary || report.buy_timing_summary || "-";
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
