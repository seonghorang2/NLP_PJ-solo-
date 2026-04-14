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
const evidenceList = document.getElementById("evidence-list");
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

function renderEvidence(values) {
  evidenceList.innerHTML = "";
  const list = toList(values);
  if (list.length === 0) {
    evidenceList.innerHTML = '<p class="placeholder">표시할 근거 리뷰가 없습니다.</p>';
    return;
  }

  list.slice(0, 8).forEach((item) => {
    const stance =
      item.stance === "negative"
        ? "주의 리뷰"
        : item.stance === "positive"
          ? "긍정 리뷰"
          : "혼합 리뷰";
    const aspect = item.aspect_label || item.aspect || "-";

    const card = document.createElement("article");
    card.className = "evidence-card";
    card.innerHTML = `
      <p class="evidence-meta">${stance} · ${aspect}</p>
      <p class="evidence-text">${item.snippet || "-"}</p>
    `;
    evidenceList.appendChild(card);
  });
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
  renderEvidence(report.evidence_reviews);
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
