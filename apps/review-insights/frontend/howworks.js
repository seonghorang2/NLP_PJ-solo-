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
const mainDetailFormulas = document.getElementById("main-detail-formulas");
const mainDetailFormulaExample = document.getElementById("main-detail-formula-example");

let selectedStageNo = null;

const DECISION_TRACE_TOOLTIP =
  "rule_decision=규칙 판정 결과, rule_confidence=규칙 신뢰도(0~1), final_decision_source=최종 판정 출처(rule/llm)";
const LLM_INVOKED_TOOLTIP =
  "이번 실행에서 LLM에 실제로 보낸 리뷰 수입니다. 보통 max_llm_reviews 상한과 함께 해석합니다.";
const RULE_FALLBACK_TOOLTIP =
  "LLM 결과를 쓰지 못해 규칙 기반 텍스트로 대체한 횟수입니다. 스키마 실패, 저신뢰, 응답 이상이 대표 원인입니다.";
const RULE_MAX_LLM_TOOLTIP =
  "포함 리뷰 전체를 보내지 않고, 리포트에 가장 도움이 되는 후보만 상한(max_llm_reviews)까지 선택합니다.";
const RULE_CANDIDATE_PRIORITY_TOOLTIP =
  "후보 우선순위는 태그/테마 유무, 플레이타임, 작성자 리뷰 수, 텍스트 길이, 최신성을 함께 반영해 정합니다.";
const RULE_JSON_SCHEMA_TOOLTIP =
  "LLM 출력은 1~4문장 JSON 스키마를 강제해 파싱 안정성과 후속 렌더 일관성을 확보합니다.";
const RULE_FALLBACK_REPLACE_TOOLTIP =
  "스키마 실패 또는 신뢰도 미달이면 LLM 결과를 버리고 fallback 텍스트로 대체해 파이프라인 안정성을 유지합니다.";

const METRIC_TOOLTIP_RULES = [
  {
    keyIncludes: "태그 없음 비율",
    tooltip:
      "분석 대상 리뷰 중 category_tags가 비어 있는 비율입니다. 값이 낮을수록 규칙 분류가 잘 되고 있다는 뜻입니다.",
  },
  {
    keyIncludes: "대표 테마 없음 비율",
    tooltip:
      "분석 대상 리뷰 중 canonical_theme가 비어 있는 비율입니다. 값이 높으면 테마 사전 보강이 필요하다는 신호입니다.",
  },
];

const CORE_RULE_TOOLTIP_RULES = [
  {
    textIncludes: "analysis_eligible=true",
    tooltip:
      "분석 최소 조건을 통과한 데이터에만 집계를 수행합니다. 표본이 너무 작은 경우 과신을 막기 위한 안전장치입니다.",
  },
  {
    textIncludes: "mention_count/negative_ratio",
    tooltip:
      "카테고리별 언급량(mention_count)과 부정 비율(negative_ratio)을 함께 계산해, 자주 나오고 불만이 큰 이슈를 찾습니다.",
  },
  {
    textIncludes: "up/down/flat/limited",
    tooltip:
      "주차 단위로 최근 흐름을 판단합니다. up=악화/증가, down=완화/감소, flat=변화 적음, limited=데이터 부족입니다.",
  },
  {
    textIncludes: "sample_size_tier",
    tooltip:
      "표본 규모를 small/medium/large 같은 등급으로 나눠 결과 신뢰도를 함께 해석할 수 있게 합니다.",
  },
  {
    textIncludes: "top themes",
    tooltip:
      "반복적으로 많이 나온 대표 테마를 집계합니다. 리포트의 강점/리스크 문장을 만드는 핵심 재료입니다.",
  },
  {
    textIncludes: "rule_decision/rule_confidence/final_decision_source",
    tooltip: DECISION_TRACE_TOOLTIP,
  },
];

const DEFAULT_STAGE_FORMULAS = {
  1: [
    "raw_review_count = len(dedup_by_review_id(raw_reviews))",
  ],
  2: [
    "hangul_ratio = hangul_char_count / visible_char_count",
    "included_in_analysis = not(is_low_quality or is_profanity_only or hangul_ratio < 0.20)",
    "analysis_eligible = (included_review_count >= 100)",
    "rule_confidence = clamp(0.45 + min(hangul_ratio,0.90)*0.25 + min(visible_len/120,1.0)*0.20 + (has_tags?0.10:-0.05) - min(0.05*ambiguity_flag_count,0.25), 0, 1)",
  ],
  3: [
    "N = included_review_count",
    "high_min_mentions = max(12, round(N * 0.06))",
    "medium_min_mentions = max(6, round(N * 0.03))",
    "mention_count(category) = number_of_included_reviews_with_category",
    "negative_ratio(category) = negative_count / mention_count",
  ],
  4: [
    "selected_candidates = top_k(included_reviews, max_llm_reviews)",
    "llm_applied = (decision != null and confidence >= min_confidence)",
    "fallback_used = (decision == null) or (confidence < min_confidence)",
  ],
  5: [
    "severe = count(selected_risks where negative_ratio >= 0.65)",
    "medium = count(selected_risks where negative_ratio >= 0.52)",
    "if severe>=2 -> not_recommended; elif declining and (severe>=1 or medium>=2) -> wait; elif severe==0 and medium<=1 and recent in {stable,improving} -> buy_now; else -> buy_on_sale",
  ],
  6: [
    "quick_decision_score_4 = I(decision_core_ready) + I(fit_ready) + I(evidence_ready) + I(forbidden_label_exposure_count==0)",
    "evidence_mismatch_rate = mismatch_count / checked_count",
    "evidence_unknown_snippet_rate = unknown_count / (checked_count + unknown_count)",
    "gate_pass = (quick_decision_score_4 >= min_score) and (evidence_unknown_snippet_rate <= max_unknown_snippet_rate)",
  ],
  7: [
    "snapshot_version = v + timestamp",
    "stored_artifacts = {raw, processed, analysis, metadata, report}",
  ],
  8: [
    "snapshot_found = exists(report_snapshot_for_selected_appid)",
  ],
  9: [
    "http_status = 200 if (snapshot_found and analysis_eligible) else non-200",
    "response_time_ms = t_response - t_request",
  ],
  10: [
    "delta_review_count = current_review_count - last_review_count",
  ],
  11: [
    "needs_refresh = (delta_review_count >= threshold_n)",
  ],
  12: [
    "if needs_refresh: run_offline_pipeline(); replace_latest_snapshot()",
  ],
};

const FORMULA_TOOLTIP_RULES = [
  {
    includes: "N",
    tooltip: "N은 분석 포함 리뷰 수(included_review_count)입니다.",
  },
  {
    includes: "high_min_mentions",
    tooltip: "high_min_mentions는 고합의 기준 최소 언급 수입니다. max(12, round(N*0.06))으로 계산합니다.",
  },
  {
    includes: "medium_min_mentions",
    tooltip: "medium_min_mentions는 중간 합의 기준 최소 언급 수입니다. max(6, round(N*0.03))으로 계산합니다.",
  },
  {
    includes: "negative_ratio",
    tooltip: "negative_ratio는 해당 카테고리에서 부정 리뷰 비율입니다. negative_count / mention_count 입니다.",
  },
  {
    includes: "hangul_ratio",
    tooltip: "hangul_ratio는 보이는 문자 중 한글(가-힣) 비율입니다.",
  },
  {
    includes: "rule_confidence",
    tooltip: "rule_confidence는 규칙 판정의 확신도(0~1)입니다. 높을수록 규칙 판정이 안정적입니다.",
  },
  {
    includes: "quick_decision_score_4",
    tooltip: "quick_decision_score_4는 핵심 4조건 충족 개수입니다. 0~4 점수로 계산합니다.",
  },
  {
    includes: "evidence_unknown_snippet_rate",
    tooltip: "근거 스니펫 중 긍/부정을 판정하지 못한 비율입니다. 높으면 근거 품질 경고 신호입니다.",
  },
];

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

function findMetricTooltip(key) {
  const safeKey = String(key || "");
  const lowerKey = safeKey.toLowerCase();

  if (safeKey.includes("LLM 호출 수") || lowerKey.includes("llm")) {
    return LLM_INVOKED_TOOLTIP;
  }
  if (safeKey.includes("규칙 대체 사용 수") || lowerKey.includes("fallback")) {
    return RULE_FALLBACK_TOOLTIP;
  }

  if (
    (safeKey.includes("태그") && safeKey.includes("없음") && safeKey.includes("비율")) ||
    lowerKey.includes("untagged")
  ) {
    return "분석 대상 리뷰 중 category_tags가 비어 있는 비율입니다. 값이 낮을수록 규칙 분류가 잘 되고 있다는 뜻입니다.";
  }
  if (
    (safeKey.includes("대표") && safeKey.includes("테마") && safeKey.includes("없음") && safeKey.includes("비율")) ||
    lowerKey.includes("theme_missing")
  ) {
    return "분석 대상 리뷰 중 canonical_theme가 비어 있는 비율입니다. 값이 높으면 테마 사전 보강이 필요하다는 신호입니다.";
  }

  const matched = METRIC_TOOLTIP_RULES.find((item) =>
    safeKey.includes(item.keyIncludes)
  );
  return matched ? matched.tooltip : "";
}

function findCoreRuleTooltip(ruleText) {
  const safeText = String(ruleText || "");
  const lowerText = safeText.toLowerCase();

  if (safeText.includes("max_llm_reviews")) {
    return RULE_MAX_LLM_TOOLTIP;
  }
  if (
    safeText.includes("태그/테마") ||
    safeText.includes("플레이타임") ||
    safeText.includes("작성자")
  ) {
    return RULE_CANDIDATE_PRIORITY_TOOLTIP;
  }
  if (safeText.includes("1~4") && safeText.includes("JSON")) {
    return RULE_JSON_SCHEMA_TOOLTIP;
  }
  if (lowerText.includes("fallback")) {
    return RULE_FALLBACK_REPLACE_TOOLTIP;
  }

  const matched = CORE_RULE_TOOLTIP_RULES.find((item) =>
    safeText.includes(item.textIncludes)
  );
  return matched ? matched.tooltip : "";
}

function findFormulaTooltip(formulaText) {
  const safeText = String(formulaText || "");
  const matched = FORMULA_TOOLTIP_RULES.find((item) =>
    safeText.includes(item.includes)
  );
  return matched ? matched.tooltip : "";
}

function parseNumberLike(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const text = String(value ?? "").trim();
  if (!text) {
    return null;
  }
  const normalized = text.replace(/,/g, "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function pickStageNumber(stage, keys) {
  const input = toObject(stage && stage.input);
  const output = toObject(stage && stage.output);
  const metrics = toObject(stage && stage.metrics);
  for (const key of keys) {
    const fromInput = parseNumberLike(input[key]);
    if (fromInput !== null) {
      return fromInput;
    }
    const fromOutput = parseNumberLike(output[key]);
    if (fromOutput !== null) {
      return fromOutput;
    }
    const fromMetrics = parseNumberLike(metrics[key]);
    if (fromMetrics !== null) {
      return fromMetrics;
    }
  }
  return null;
}

function formatExampleNumber(value, digits = 0) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  if (digits > 0) {
    return value.toFixed(digits);
  }
  return String(Math.round(value));
}

function buildFormulaExample(stage) {
  const stageNo = Number(stage && stage.stage_no);

  if (stageNo === 3) {
    const n = pickStageNumber(stage, ["included_review_count", "분석 포함 리뷰 수"]);
    if (n !== null) {
      const high = Math.max(12, Math.round(n * 0.06));
      const medium = Math.max(6, Math.round(n * 0.03));
      return `실제 값 대입 예시: N=${formatExampleNumber(n)} -> high_min_mentions=max(12, round(N*0.06))=${high}, medium_min_mentions=max(6, round(N*0.03))=${medium}`;
    }
  }

  if (stageNo === 2) {
    const included = pickStageNumber(stage, ["included_review_count", "분석 포함 리뷰 수"]);
    if (included !== null) {
      return `실제 값 대입 예시: included_review_count=${formatExampleNumber(included)} -> analysis_eligible = (${formatExampleNumber(included)} >= 100) = ${included >= 100}`;
    }
  }

  if (stageNo === 6) {
    const mismatch = pickStageNumber(stage, ["근거 불일치율", "evidence_mismatch_rate"]);
    const unknown = pickStageNumber(stage, ["근거 판정불가율", "evidence_unknown_snippet_rate"]);
    if (mismatch !== null || unknown !== null) {
      return `실제 값 대입 예시: evidence_mismatch_rate=${mismatch !== null ? formatExampleNumber(mismatch, 4) : "-"}, evidence_unknown_snippet_rate=${unknown !== null ? formatExampleNumber(unknown, 4) : "-"}`;
    }
  }

  if (stageNo === 10) {
    const last = pickStageNumber(stage, ["last_review_count"]);
    const current = pickStageNumber(stage, ["current_review_count"]);
    if (last !== null && current !== null) {
      const delta = current - last;
      return `실제 값 대입 예시: delta_review_count = ${formatExampleNumber(current)} - ${formatExampleNumber(last)} = ${formatExampleNumber(delta)}`;
    }
  }

  if (stageNo === 11) {
    const delta = pickStageNumber(stage, ["delta_review_count", "신규 리뷰 수"]);
    const threshold = pickStageNumber(stage, ["threshold_n", "임계치 n"]);
    if (delta !== null && threshold !== null) {
      return `실제 값 대입 예시: needs_refresh = (${formatExampleNumber(delta)} >= ${formatExampleNumber(threshold)}) = ${delta >= threshold}`;
    }
  }

  return "실제 값 대입 예시: 현재 단계에서 공개 가능한 샘플 값이 없습니다.";
}

function appendInlineTooltip(li, tooltipText) {
  const safeTooltip = String(tooltipText || "").trim();
  if (!safeTooltip) {
    return;
  }
  li.classList.add("has-inline-tooltip");
  const tip = document.createElement("span");
  tip.className = "inline-tooltip-hint";
  tip.textContent = " (i)";
  tip.setAttribute("tabindex", "0");
  tip.setAttribute("data-tooltip", safeTooltip);
  tip.setAttribute("aria-label", safeTooltip);
  li.appendChild(tip);
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
    appendInlineTooltip(li, findMetricTooltip(key));
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
    appendInlineTooltip(li, findCoreRuleTooltip(rule));
    container.appendChild(li);
  });
}

function formulaEntries(stage) {
  const scoring = toObject(stage && stage.scoring);
  const scoringFormula = String(scoring.formula || "").trim();
  const scoringWeights = Object.entries(toObject(scoring.weights));
  const scoringEntries = [];

  if (scoringFormula) {
    scoringEntries.push(`scoring.formula: ${scoringFormula}`);
  }
  if (scoringWeights.length) {
    const weightText = scoringWeights
      .map(([key, value]) => `${key}=${value}`)
      .join(", ");
    scoringEntries.push(`scoring.weights: ${weightText}`);
  }

  const explicit = toArray(stage && stage.core_formulas)
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  if (explicit.length) {
    return [...scoringEntries, ...explicit];
  }
  const stageNo = Number(stage && stage.stage_no);
  return [...scoringEntries, ...toArray(DEFAULT_STAGE_FORMULAS[stageNo])];
}

function renderFormulaList(container, stage) {
  container.innerHTML = "";
  const formulas = formulaEntries(stage);
  if (!formulas.length) {
    const li = document.createElement("li");
    li.textContent = "표시할 핵심 수식이 없습니다.";
    container.appendChild(li);
    if (mainDetailFormulaExample) {
      mainDetailFormulaExample.textContent = "실제 값 대입 예시: -";
    }
    return;
  }
  formulas.forEach((formula) => {
    const li = document.createElement("li");
    li.textContent = formula;
    appendInlineTooltip(li, findFormulaTooltip(formula));
    container.appendChild(li);
  });
  if (mainDetailFormulaExample) {
    mainDetailFormulaExample.textContent = buildFormulaExample(stage);
  }
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
  renderFormulaList(mainDetailFormulas, stage);
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
      data.note || "설명용 mock 데이터이며 실제 운영 흐름과 일부 차이가 있을 수 있습니다."
    );
    markLoadedTime();
  } catch (error) {
    loadedAt.textContent = "데이터 로딩 실패";
    mainFlowGrid.innerHTML = `<p>${error.message || "알 수 없는 오류가 발생했습니다."}</p>`;
    mockNote.textContent = "mock 데이터 파일 경로 또는 서버 상태를 확인해 주세요.";
  }
}

bootstrap();
