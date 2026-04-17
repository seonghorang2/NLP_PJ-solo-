const mainFlowGrid = document.getElementById("main-flow-grid");
const updateLoopGrid = document.getElementById("update-loop-grid");
const loadedAt = document.getElementById("loaded-at");
const mockNote = document.getElementById("mock-note");

const mainDetailTrack = document.getElementById("main-detail-track");
const mainDetailTitle = document.getElementById("main-detail-title");
const mainDetailInput = document.getElementById("main-detail-input");
const mainDetailOutput = document.getElementById("main-detail-output");
const mainDetailMetrics = document.getElementById("main-detail-metrics");

const loopDetailTitle = document.getElementById("loop-detail-title");
const loopDetailInput = document.getElementById("loop-detail-input");
const loopDetailOutput = document.getElementById("loop-detail-output");
const loopDetailMetrics = document.getElementById("loop-detail-metrics");

let selectedMainStageNo = null;
let selectedLoopStepNo = null;

function toObject(value) {
  return value && typeof value === "object" ? value : {};
}

function toArray(value) {
  return Array.isArray(value) ? value : [];
}

function prettyObject(value) {
  const safe = toObject(value);
  if (Object.keys(safe).length === 0) {
    return "{}";
  }
  return JSON.stringify(safe, null, 2);
}

function metricEntries(metrics) {
  return Object.entries(toObject(metrics));
}

function metricPreview(metrics, maxCount = 2) {
  return metricEntries(metrics)
    .slice(0, maxCount)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" / ");
}

function renderMetricList(container, metrics) {
  container.innerHTML = "";
  const entries = metricEntries(metrics);
  if (!entries.length) {
    const li = document.createElement("li");
    li.textContent = "표시할 지표가 없습니다.";
    container.appendChild(li);
    return;
  }
  entries.forEach(([key, value]) => {
    const li = document.createElement("li");
    li.textContent = `${key}: ${value}`;
    container.appendChild(li);
  });
}

function trackTypeByStage(stageNo) {
  return Number(stageNo) <= 7 ? "offline" : "online";
}

function trackLabel(trackType) {
  return trackType === "offline" ? "오프라인" : "온라인";
}

function setMainDetail(stage) {
  const stageNo = Number(stage.stage_no);
  const stageName = String(stage.stage_name || "-");
  const trackType = trackTypeByStage(stageNo);

  mainDetailTrack.textContent = trackLabel(trackType);
  mainDetailTrack.className = `track-chip ${trackType === "online" ? "online" : ""}`;
  mainDetailTitle.textContent = `${stageNo}. ${stageName}`;
  mainDetailInput.textContent = prettyObject(stage.input);
  mainDetailOutput.textContent = prettyObject(stage.output);
  renderMetricList(mainDetailMetrics, stage.metrics);
}

function setLoopDetail(step) {
  const stepNo = Number(step.step_no);
  const stepName = String(step.step_name || "-");

  loopDetailTitle.textContent = `${stepNo}. ${stepName}`;
  loopDetailInput.textContent = prettyObject(step.input);
  loopDetailOutput.textContent = prettyObject(step.output);
  renderMetricList(loopDetailMetrics, step.metrics);
}

function renderMainFlow(mainFlow) {
  mainFlowGrid.innerHTML = "";
  const items = toArray(mainFlow);
  if (!items.length) {
    mainFlowGrid.innerHTML = "<p>표시할 메인 플로우 데이터가 없습니다.</p>";
    return;
  }

  if (selectedMainStageNo === null) {
    selectedMainStageNo = Number(items[0].stage_no);
  }

  items.forEach((stage) => {
    const stageNo = Number(stage.stage_no);
    const stageName = String(stage.stage_name || "-");
    const trackType = trackTypeByStage(stageNo);

    const button = document.createElement("button");
    button.type = "button";
    button.className = `stage-card ${trackType}${selectedMainStageNo === stageNo ? " active" : ""}`;
    button.innerHTML = `
      <div class="top">
        <span class="index">${stageNo}</span>
        <span class="track">${trackLabel(trackType)}</span>
      </div>
      <p class="name">${stageName}</p>
      <p class="metric-preview">${metricPreview(stage.metrics) || "핵심 지표 없음"}</p>
    `;
    button.addEventListener("click", () => {
      selectedMainStageNo = stageNo;
      renderMainFlow(items);
      setMainDetail(stage);
    });
    mainFlowGrid.appendChild(button);

    if (selectedMainStageNo === stageNo) {
      setMainDetail(stage);
    }
  });
}

function renderUpdateLoop(updateLoop) {
  updateLoopGrid.innerHTML = "";
  const items = toArray(updateLoop);
  if (!items.length) {
    updateLoopGrid.innerHTML = "<p>표시할 업데이트 루프 데이터가 없습니다.</p>";
    return;
  }

  if (selectedLoopStepNo === null) {
    selectedLoopStepNo = Number(items[0].step_no);
  }

  items.forEach((step) => {
    const stepNo = Number(step.step_no);
    const stepName = String(step.step_name || "-");
    const button = document.createElement("button");
    button.type = "button";
    button.className = `loop-card${selectedLoopStepNo === stepNo ? " active" : ""}`;
    button.innerHTML = `
      <p class="loop-title">${stepNo}. ${stepName}</p>
      <p class="loop-preview">${metricPreview(step.metrics) || "핵심 지표 없음"}</p>
    `;
    button.addEventListener("click", () => {
      selectedLoopStepNo = stepNo;
      renderUpdateLoop(items);
      setLoopDetail(step);
    });
    updateLoopGrid.appendChild(button);

    if (selectedLoopStepNo === stepNo) {
      setLoopDetail(step);
    }
  });
}

async function loadHowworksData() {
  const response = await fetch("/mock/howworks_pipeline.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("설명용 mock 데이터를 불러오지 못했습니다.");
  }
  return response.json();
}

function markLoadedTime() {
  const now = new Date();
  loadedAt.textContent = `데이터 로드 시각: ${now.toLocaleString("ko-KR")}`;
}

async function bootstrap() {
  loadedAt.textContent = "데이터 로딩 중...";
  try {
    const payload = await loadHowworksData();
    const data = toObject(payload.pipeline_overview_mock);

    renderMainFlow(data.main_flow);
    renderUpdateLoop(data.update_loop);
    mockNote.textContent = String(
      data.note || "설명용 mock 데이터이며, 실제 운영 흐름과는 일부 차이가 있을 수 있습니다."
    );
    markLoadedTime();
  } catch (error) {
    loadedAt.textContent = "데이터 로딩 실패";
    mainFlowGrid.innerHTML = `<p>${error.message || "알 수 없는 오류가 발생했습니다."}</p>`;
    updateLoopGrid.innerHTML = "<p>업데이트 루프를 표시할 수 없습니다.</p>";
    mockNote.textContent = "mock 데이터 파일 경로 또는 서버 라우트를 확인해 주세요.";
  }
}

bootstrap();
