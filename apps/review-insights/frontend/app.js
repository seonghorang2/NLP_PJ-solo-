const form = document.getElementById("ingest-form");
const compareForm = document.getElementById("compare-form");
const appidInput = document.getElementById("appid-input");
const compareAppid1Input = document.getElementById("compare-appid-1");
const compareAppid2Input = document.getElementById("compare-appid-2");
const runButton = document.getElementById("run-button");
const compareButton = document.getElementById("compare-button");
const statusPanel = document.getElementById("status-panel");
const sampleTier = document.getElementById("sample-tier");
const trendStatus = document.getElementById("trend-status");
const issueCount = document.getElementById("issue-count");
const warningsList = document.getElementById("warnings-list");
const issueSignals = document.getElementById("issue-signals");
const summaryPanel = document.getElementById("summary-panel");
const jsonView = document.getElementById("json-view");
const rawView = document.getElementById("raw-view");
const processedView = document.getElementById("processed-view");
const processedFilterMode = document.getElementById("processed-filter-mode");
const processedCount = document.getElementById("processed-count");
const comparisonPanel = document.getElementById("comparison-panel");
const comparisonView = document.getElementById("comparison-view");

let latestRawReviews = [];
let latestProcessedReviews = [];

function setStatus(message, type = "info") {
  statusPanel.textContent = message;
  statusPanel.className = `status-panel ${type}`;
}

function renderWarnings(warnings) {
  warningsList.innerHTML = "";

  if (!warnings || warnings.length === 0) {
    warningsList.innerHTML = '<li class="placeholder">표시할 경고가 없습니다.</li>';
    return;
  }

  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warning;
    warningsList.appendChild(item);
  });
}

function renderIssueSignals(signals) {
  issueSignals.innerHTML = "";
  const entries = Object.entries(signals || {});

  if (entries.length === 0) {
    issueSignals.innerHTML = '<p class="placeholder">표시할 이슈 신호가 없습니다.</p>';
    return;
  }

  entries.forEach(([category, signal]) => {
    const card = document.createElement("article");
    card.className = "issue-card";
    card.innerHTML = `
      <div class="issue-card-head">
        <h3>${category}</h3>
        <span class="trend-pill ${signal.recent_trend}">${signal.recent_trend}</span>
      </div>
      <p class="issue-meta">언급 수 ${signal.mention_count}건 · 부정 비율 ${(signal.negative_ratio * 100).toFixed(0)}%</p>
      <p class="issue-meta">숙련 유저 비중 ${(signal.experienced_player_share * 100).toFixed(0)}%</p>
      <p class="issue-label">대표 테마</p>
      <p class="issue-value">${(signal.themes || []).join(", ") || "없음"}</p>
      <p class="issue-label">대표 리뷰</p>
      <p class="issue-value">${(signal.sample_reviews || []).join(" / ") || "없음"}</p>
    `;
    issueSignals.appendChild(card);
  });
}

function prettifySummaryKey(key) {
  const labelMap = {
    what_players_like: "플레이어가 좋아하는 점",
    what_players_dislike: "플레이어가 불편해하는 점",
    recent_change: "최근 변화",
    fit_for: "어떤 플레이어에게 맞는지",
    risks: "주의할 리스크",
  };
  return labelMap[key] || key;
}

function renderSummary(summary) {
  summaryPanel.innerHTML = "";
  const entries = Object.entries(summary || {});

  if (entries.length === 0) {
    summaryPanel.innerHTML = '<p class="placeholder">아직 요약 결과가 없습니다.</p>';
    return;
  }

  entries.forEach(([key, value]) => {
    const block = document.createElement("div");
    block.className = "summary-block";
    block.innerHTML = `<strong>${prettifySummaryKey(key)}</strong><p>${value || "-"}</p>`;
    summaryPanel.appendChild(block);
  });
}

function getVisibleProcessedReviews() {
  const mode = processedFilterMode ? processedFilterMode.value : "all";
  if (mode === "included") {
    return latestProcessedReviews.filter((review) => review.included_in_analysis);
  }
  if (mode === "excluded") {
    return latestProcessedReviews.filter((review) => !review.included_in_analysis);
  }
  if (mode === "all") {
    return latestProcessedReviews;
  }
  return latestProcessedReviews;
}

function renderProcessedView() {
  const visible = getVisibleProcessedReviews();
  processedView.textContent = JSON.stringify(visible, null, 2);

  if (processedCount) {
    processedCount.textContent = `${visible.length} / ${latestProcessedReviews.length}`;
  }
}

function renderDebugViews(rawReviews, processedReviews) {
  latestRawReviews = rawReviews || [];
  latestProcessedReviews = processedReviews || [];

  rawView.textContent = JSON.stringify(latestRawReviews, null, 2);
  renderProcessedView();
}

function renderResult(result) {
  sampleTier.textContent = result.sample_size_tier || "-";
  trendStatus.textContent = result.trend_status || "-";
  issueCount.textContent = Object.keys(result.issue_signals || {}).length.toString();
  renderWarnings(result.warnings || []);
  renderIssueSignals(result.issue_signals || {});
  renderSummary(result.summary || {});
  jsonView.textContent = JSON.stringify(result, null, 2);
}

function renderComparison(comparison) {
  comparisonView.textContent = JSON.stringify(comparison || {}, null, 2);

  if (!comparison) {
    comparisonPanel.innerHTML = '<p class="placeholder">비교 결과가 없습니다.</p>';
    return;
  }

  const warnings = comparison.warnings || [];
  const shared = comparison.shared_issue_categories || [];
  const unique1 = comparison.unique_to_game_1 || [];
  const unique2 = comparison.unique_to_game_2 || [];
  const game1 = comparison.game_1 || {};
  const game2 = comparison.game_2 || {};
  const metadata1 = game1.metadata || {};
  const metadata2 = game2.metadata || {};

  comparisonPanel.innerHTML = `
    <div class="comparison-block">
      <strong>비교 상태</strong>
      <p>${comparison.comparison_status || "-"} / ${comparison.comparison_reason || "-"}</p>
    </div>
    <div class="comparison-block">
      <strong>비교 요약</strong>
      <p>${comparison.comparison_summary || "-"}</p>
    </div>
    <div class="comparison-grid">
      <div class="comparison-card">
        <strong>게임 1 (${game1.appid || "-"})</strong>
        <p>표본 등급: ${game1.sample_size_tier || "-"}</p>
        <p>트렌드 상태: ${game1.trend_status || "-"}</p>
        <p>이슈 수: ${game1.issue_count ?? "-"}</p>
        <p>장르: ${(metadata1.genres || []).join(", ") || "-"}</p>
        <p>가격 모델: ${metadata1.price_model || "-"}</p>
        <p>출시 단계: ${metadata1.release_stage || "-"}</p>
      </div>
      <div class="comparison-card">
        <strong>게임 2 (${game2.appid || "-"})</strong>
        <p>표본 등급: ${game2.sample_size_tier || "-"}</p>
        <p>트렌드 상태: ${game2.trend_status || "-"}</p>
        <p>이슈 수: ${game2.issue_count ?? "-"}</p>
        <p>장르: ${(metadata2.genres || []).join(", ") || "-"}</p>
        <p>가격 모델: ${metadata2.price_model || "-"}</p>
        <p>출시 단계: ${metadata2.release_stage || "-"}</p>
      </div>
    </div>
    <div class="comparison-grid">
      <div class="comparison-card">
        <strong>공통 이슈</strong>
        <p>${shared.join(", ") || "없음"}</p>
      </div>
      <div class="comparison-card">
        <strong>게임 1만 있는 이슈</strong>
        <p>${unique1.join(", ") || "없음"}</p>
      </div>
      <div class="comparison-card">
        <strong>게임 2만 있는 이슈</strong>
        <p>${unique2.join(", ") || "없음"}</p>
      </div>
    </div>
    <div class="comparison-block">
      <strong>경고</strong>
      <p>${warnings.join(" / ") || "없음"}</p>
    </div>
  `;
}

async function runIngestion(appid) {
  const ingestResponse = await fetch("/api/ingest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ appid }),
  });

  if (!ingestResponse.ok) {
    const errorPayload = await ingestResponse.json().catch(() => ({}));
    throw new Error(errorPayload.detail || "분석 실행에 실패했습니다.");
  }

  return ingestResponse.json();
}

async function loadJson(url, fallbackMessage) {
  const response = await fetch(url);

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.detail || fallbackMessage);
  }

  return response.json();
}

async function loadAnalysis(appid) {
  return loadJson(`/api/games/${appid}/analysis`, "분석 결과를 불러오지 못했습니다.");
}

async function loadRaw(appid) {
  return loadJson(`/api/games/${appid}/raw`, "raw 데이터를 불러오지 못했습니다.");
}

async function loadProcessed(appid) {
  return loadJson(`/api/games/${appid}/processed`, "processed 데이터를 불러오지 못했습니다.");
}

async function loadComparison(appid1, appid2) {
  return loadJson(
    `/api/compare?appid1=${appid1}&appid2=${appid2}`,
    "비교 결과를 불러오지 못했습니다.",
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const appid = Number(appidInput.value);
  if (!appid) {
    setStatus("유효한 appid를 입력해 주세요.", "error");
    return;
  }

  runButton.disabled = true;
  setStatus("리뷰를 수집하고 분석 중입니다...", "loading");

  try {
    await runIngestion(appid);
    const [analysis, rawReviews, processedReviews] = await Promise.all([
      loadAnalysis(appid),
      loadRaw(appid),
      loadProcessed(appid),
    ]);

    renderResult(analysis);
    renderDebugViews(rawReviews, processedReviews);
    setStatus("분석 결과와 디버그 데이터를 불러왔습니다.", "success");
  } catch (error) {
    setStatus(error.message || "알 수 없는 오류가 발생했습니다.", "error");
  } finally {
    runButton.disabled = false;
  }
});

compareForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const appid1 = Number(compareAppid1Input.value);
  const appid2 = Number(compareAppid2Input.value);

  if (!appid1 || !appid2) {
    setStatus("비교할 두 appid를 모두 입력해 주세요.", "error");
    return;
  }

  compareButton.disabled = true;
  setStatus("두 게임을 분석한 뒤 비교 결과를 불러오는 중입니다...", "loading");

  try {
    await Promise.all([runIngestion(appid1), runIngestion(appid2)]);
    const comparison = await loadComparison(appid1, appid2);
    renderComparison(comparison);
    setStatus("비교 결과를 불러왔습니다.", "success");
  } catch (error) {
    setStatus(error.message || "비교 중 알 수 없는 오류가 발생했습니다.", "error");
  } finally {
    compareButton.disabled = false;
  }
});

if (processedFilterMode) {
  processedFilterMode.addEventListener("change", () => {
    renderProcessedView();
  });
}
