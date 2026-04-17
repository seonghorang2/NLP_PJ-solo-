const mainFlowGrid = document.getElementById("main-flow-grid");
const loadedAt = document.getElementById("loaded-at");
const mockNote = document.getElementById("mock-note");

const mainDetailTrack = document.getElementById("main-detail-track");
const mainDetailStatus = document.getElementById("main-detail-status");
const mainDetailTitle = document.getElementById("main-detail-title");
const mainDetailInput = document.getElementById("main-detail-input");
const mainDetailOutput = document.getElementById("main-detail-output");
const mainDetailMetrics = document.getElementById("main-detail-metrics");
const mainDetailCoreRules = document.getElementById("main-detail-core-rules");

let selectedStageNo = null;

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

function statusValue(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "planned" ? "planned" : "implemented";
}

function cardStatusLabel(value) {
  return statusValue(value) === "planned" ? "업데이트 루프" : "메인 루프";
}

function detailStatusLabel(value, trackType) {
  if (trackType === "update" && statusValue(value) === "planned") {
    return "업데이트 루프";
  }
  return statusValue(value) === "planned" ? "실서비스 기준 구현" : "메인 루프";
}

function statusClass(value) {
  return statusValue(value) === "planned" ? "planned" : "implemented";
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

function renderCoreRules(container, coreRules) {
  container.innerHTML = "";
  const rules = toArray(coreRules)
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  if (!rules.length) {
    const li = document.createElement("li");
    li.textContent = "표시할 핵심 규칙이 없습니다.";
    container.appendChild(li);
    return;
  }
  rules.forEach((rule) => {
    const li = document.createElement("li");
    li.textContent = rule;
    container.appendChild(li);
  });
}

function resolveTrackType(stage) {
  const explicit = String(stage.track_type || "").trim().toLowerCase();
  if (explicit === "offline" || explicit === "online" || explicit === "update") {
    return explicit;
  }
  const stageNo = Number(stage.stage_no);
  if (stageNo <= 7) {
    return "offline";
  }
  if (stageNo <= 9) {
    return "online";
  }
  return "update";
}

function trackLabel(trackType) {
  if (trackType === "offline") {
    return "오프라인";
  }
  if (trackType === "online") {
    return "온라인";
  }
  return "업데이트 루프";
}

function setMainDetail(stage) {
  const stageNo = Number(stage.stage_no);
  const stageName = String(stage.stage_name || "-");
  const trackType = resolveTrackType(stage);
  const implStatus = statusValue(stage.implementation_status);

  if (trackType === "update" && implStatus === "planned") {
    mainDetailTrack.textContent = "실서비스 기준 구현";
    mainDetailTrack.className = "track-chip update";
  } else {
    mainDetailTrack.textContent = trackLabel(trackType);
    mainDetailTrack.className = `track-chip ${
      trackType === "online" ? "online" : trackType === "update" ? "update" : ""
    }`;
  }

  mainDetailStatus.textContent = detailStatusLabel(implStatus, trackType);
  mainDetailStatus.className = `status-chip ${statusClass(implStatus)}`;
  mainDetailTitle.textContent = `${stageNo}. ${stageName}`;
  mainDetailInput.textContent = prettyObject(stage.input);
  mainDetailOutput.textContent = prettyObject(stage.output);
  renderMetricList(mainDetailMetrics, stage.metrics);
  renderCoreRules(mainDetailCoreRules, stage.core_rules);
}

function renderMainFlow(stages) {
  mainFlowGrid.innerHTML = "";
  const items = toArray(stages);
  if (!items.length) {
    mainFlowGrid.innerHTML = "<p>표시할 통합 플로우 데이터가 없습니다.</p>";
    return;
  }

  if (selectedStageNo === null) {
    selectedStageNo = Number(items[0].stage_no);
  }

  items.forEach((stage) => {
    const stageNo = Number(stage.stage_no);
    const stageName = String(stage.stage_name || "-");
    const trackType = resolveTrackType(stage);
    const implStatus = statusValue(stage.implementation_status);

    const button = document.createElement("button");
    button.type = "button";
    button.className = `stage-card ${trackType}${selectedStageNo === stageNo ? " active" : ""}`;
    button.innerHTML = `
      <div class="top">
        <span class="index">${stageNo}</span>
        <span class="track">${trackLabel(trackType)}</span>
      </div>
      <span class="impl-badge ${statusClass(implStatus)}">${cardStatusLabel(implStatus)}</span>
      <p class="name">${stageName}</p>
      <p class="metric-preview">${metricPreview(stage.metrics) || "핵심 지표 없음"}</p>
    `;
    button.addEventListener("click", () => {
      selectedStageNo = stageNo;
      renderMainFlow(items);
      setMainDetail(stage);
    });
    mainFlowGrid.appendChild(button);

    if (selectedStageNo === stageNo) {
      setMainDetail(stage);
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

function buildUnifiedFlow(data) {
  const mainStages = toArray(data.main_flow).map((stage) => ({
    ...toObject(stage),
    stage_no: Number(stage.stage_no),
    track_type: "offline",
  }));

  const normalizedMain = mainStages.map((stage) => {
    if (Number(stage.stage_no) >= 8) {
      return { ...stage, track_type: "online" };
    }
    return stage;
  });

  const updateStages = toArray(data.update_loop).map((step, index) => ({
    stage_no: 10 + index,
    stage_name: String(step.step_name || `업데이트 단계 ${index + 1}`),
    implementation_status: String(step.implementation_status || "planned"),
    input: toObject(step.input),
    output: toObject(step.output),
    metrics: toObject(step.metrics),
    core_rules: toArray(step.core_rules),
    track_type: "update",
  }));

  const merged = [...normalizedMain, ...updateStages];
  const flowOrder = toArray(data.flow_order)
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));

  if (!flowOrder.length) {
    return merged.sort((a, b) => Number(a.stage_no) - Number(b.stage_no));
  }

  const byStageNo = new Map(merged.map((stage) => [Number(stage.stage_no), stage]));
  const ordered = [];
  const used = new Set();
  flowOrder.forEach((stageNo) => {
    const stage = byStageNo.get(Number(stageNo));
    if (!stage) {
      return;
    }
    ordered.push(stage);
    used.add(Number(stageNo));
  });

  const remaining = merged
    .filter((stage) => !used.has(Number(stage.stage_no)))
    .sort((a, b) => Number(a.stage_no) - Number(b.stage_no));
  return [...ordered, ...remaining];
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
    const unifiedStages = buildUnifiedFlow(data);

    renderMainFlow(unifiedStages);
    mockNote.textContent = String(
      data.note || "설명용 mock 데이터이며, 실제 운영 흐름과는 일부 차이가 있을 수 있습니다."
    );
    markLoadedTime();
  } catch (error) {
    loadedAt.textContent = "데이터 로딩 실패";
    mainFlowGrid.innerHTML = `<p>${error.message || "알 수 없는 오류가 발생했습니다."}</p>`;
    mockNote.textContent = "mock 데이터 파일 경로 또는 서버 라우트를 확인해 주세요.";
  }
}

bootstrap();
