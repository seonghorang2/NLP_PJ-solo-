# Steam Review Insights 파이프라인 리서치 보고서

작성일: 2026-04-15  
작성 범위: `apps/review-insights/` 전체 코드 + 운영 문서 + 테스트

---

## 1) 한눈에 보는 결론

현재 시스템은 **온디맨드 분석형이 아니라 오프라인 분석 + 온라인 조회 전용 구조**로 동작한다.

- 오프라인(수동 실행): Steam fetch -> 전처리 -> 선택적 LLM fallback -> 분석 집계 -> 구매 리포트 생성 -> 파일 저장
- 온라인(사용자 조회): 저장된 `report`/`analysis`/`processed`/`metadata`를 읽기만 수행
- 사용자 조회 경로에서 Steam API 호출/전처리/LLM 분석은 실행되지 않도록 분리됨

핵심 엔트리포인트:

- 오프라인 파이프라인: `apps/review-insights/backend/pipeline/offline_pipeline.py`
- 사용자 API: `apps/review-insights/backend/api/routes.py`
- 리포트 생성기: `apps/review-insights/backend/services/report_view.py`

---

## 2) 전체 아키텍처

### 2.1 텍스트 다이어그램

```text
[Admin Manual Trigger]
  -> POST /api/admin/ingest
  -> run_offline_pipeline_for_appid()
     -> Steam reviews fetch + metadata fetch
     -> normalize to RawReview/GameMetadata
     -> deterministic preprocess (rules + category tags)
     -> selective LLM fallback (ambiguous subset only)
     -> enrich theme + build analysis snapshot
     -> build consumer report payload (v4 planned-sections)
     -> write raw/processed/analysis/metadata/report JSON

[User]
  -> GET /api/games
  -> GET /api/games/{appid}/report
     -> read stored report if valid
     -> else build deterministic report from stored analysis+processed
     -> return immediately (no fetch/no ingestion/no preprocess/no LLM analysis)
```

### 2.2 디렉터리 책임

- `backend/api/`: read-only 사용자 API + admin 수동 ingest 라우트
- `backend/pipeline/`: 오프라인 실행 오케스트레이션
- `backend/analysis/`: 규칙기반 전처리/카테고리/테마/트렌드/요약/LLM fallback 게이트
- `backend/services/`: Steam 연동, LLM adapters, report writer/view
- `backend/storage/`: 파일 기반 저장소
- `data/`: 산출물(raw, processed, analysis, metadata, report)
- `frontend/`: 구매 판단 리포트 UI
- `scripts/`: 수동 파이프라인/품질 리포트/게이트 체크

---

## 3) 오프라인 파이프라인 상세 (실제 코드 순서)

기준 파일: `backend/pipeline/offline_pipeline.py`

### 3.1 입력 파라미터

- `appid` (필수)
- `review_pages` (`all` 또는 `1~200`)
- `use_llm_fallback` (기본 `True`)
- `max_llm_reviews` (기본 `50`)
- `llm_timeout_seconds` (기본 `20`)
- `llm_retry_limit` (기본 `2`)
- `llm_min_confidence` (기본 `0.70`)

### 3.2 Steam 수집 단계

기준 파일: `backend/services/steam_reviews.py`

- 리뷰 API 기본값:
  - `language="koreana"`
  - `filter_type="recent"` (최신순)
  - `num_per_page=100`
- `review_pages="all"`이면 내부 cap `ALL_MODE_PAGE_CAP=200`
- 페이지 병합 시 `recommendationid` 기준 중복 제거
- 메타데이터(appdetails)도 함께 수집

### 3.3 원시 스키마 정규화

- `normalize_steam_reviews()` -> `RawReview`
- `normalize_steam_game_metadata()` -> `GameMetadata`
- `RawReview` 주요 필드:
  - `review_id`, `review_text`, `voted_up`, `timestamp_created`
  - `playtime_at_review_hours`, `num_reviews`, `helpful_votes`, `author_steamid`

### 3.4 결정론 전처리

기준 파일: `backend/analysis/preprocess.py`, `backend/analysis/rules.py`, `backend/analysis/categorize.py`

순서:

1. 텍스트 정규화 (`normalize_text`)
2. 한글 비율 계산 (`hangul_ratio`)
3. 저품질 판정 (`is_low_quality_review`)
4. 욕설-only 판정 (`is_profanity_only_review`)
5. 규칙 include/exclude
   - `exclude_low_quality`
   - `exclude_profanity_only`
   - `exclude_non_korean` (`hangul_ratio < 0.20`)
   - 그 외 `include`
6. include인 경우 카테고리 멀티태깅 (`extract_category_tags`)
7. 애매성 플래그 (`detect_ambiguity_flags`)
8. 규칙 confidence 계산 (`calculate_rule_confidence`)

중요:

- include인데 태그가 비면 `unclassified_included` ambiguity flag를 추가
- 이 단계는 LLM 없이 100% 결정론

### 3.5 선택적 LLM fallback (전처리 보조)

기준 파일: `backend/analysis/llm_fallback.py`, `backend/services/llm_classifier.py`

#### 하드 제외 구역 (LLM 호출 금지)

- 빈 텍스트/기호-only
- `hangul_ratio < 0.20`
- `is_low_quality=True`
- `is_profanity_only=True`

#### 후보 게이트

- `included_in_analysis=True` 인 리뷰만 대상
- semantic signal 필요:
  - `category_tags` 존재 또는 길이/한글비율 기준 통과
- uncertainty signal 필요:
  - ambiguity flags 존재
  - include인데 category 없음
  - `rule_confidence < 0.70`

#### 후보 우선순위

`helpful_votes DESC` -> `uncertainty_score DESC` -> `timestamp_created DESC`

#### 안전장치

- 최대 호출 수 cap (`max_llm_reviews`)
- timeout / retry
- 동일 normalized_text 캐시
- schema invalid 시 규칙 유지
- confidence 미달(`llm_min_confidence`) 시 규칙 유지

#### 출력 흔적 필드

- `llm_invoked`, `llm_decision`, `llm_confidence`
- `final_decision_source` (`rule|llm`)
- `final_decision` (`include|exclude`)

### 3.6 분석 집계

기준 파일: `backend/services/analysis_service.py`, `backend/analysis/themes.py`, `backend/analysis/trends.py`, `backend/analysis/summarize.py`

- `enrich_processed_reviews()`:
  - include 리뷰의 `canonical_theme` 비어있으면 theme matcher로 보강
- `issue_signals` 생성:
  - category별 `mention_count`, `negative_ratio`, `recent_trend`, `experienced_player_share`
  - top themes / sample_reviews
- `trend_status`:
  - trend limited 여부
- summary(결정론 템플릿):
  - what_players_like/dislike/recent_change/fit_for/risks

### 3.7 소비자 리포트 생성 (v4)

기준 파일: `backend/services/report_view.py`, `backend/services/report_writer_llm.py`

멀티스테이지:

1. `report_plan` 생성
2. `report_display` 섹션별 생성
3. `evidence_sections` 생성/압축/보정

세부:

- consensus payload 구성:
  - 포함 리뷰 수 기준 high/medium 임계치 계산
  - 고합의 aspect 선별
- deterministic seed 생성 후 LLM writer로 section 단위 보강 가능
- evidence는 강점/리스크 분리, 블록당 2~3개 스니펫 유지
- 최종 price-aware 추천 매핑
- 최종 한국어 교정(규칙 + 선택적 LLM)

### 3.8 파일 저장

기준 파일: `backend/storage/file_store.py`

저장 경로:

- `data/raw/{appid}({game_name}).json`
- `data/processed/{appid}({game_name}).json`
- `data/analysis/{appid}({game_name}).json`
- `data/metadata/{appid}({game_name}).json`
- `data/report/{appid}({game_name}).json`

추가 메타(analysis payload):

- `pipeline_run_id`, `generated_at`, `source_review_count`
- `review_pages`, `fetched_pages`, `fetched_review_count`
- `all_mode_page_cap`, `all_mode_cap_reached`
- `llm_stats`

---

## 4) 온라인 서빙 경로 상세

기준 파일: `backend/api/routes.py`, `frontend/app.js`

### 4.1 허용 API

- `GET /api/games`
- `GET /api/games/{appid}/report`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`
- `GET /api/games/{appid}/raw` (debug)
- `GET /api/games/{appid}/processed` (debug)

운영 수동 트리거:

- `POST /api/admin/ingest`

### 4.2 데모 allow-list

- `data/catalog/demo_games.json` 기준
- allow-list 외 appid는 404/ValueError 처리

### 4.3 report 조회 동작

`load_report()` 동작:

1. 저장된 report 파일 로드
2. `is_consumer_report_payload()` 유효하면 그대로 반환
3. 유효하지 않으면 **저장된** `analysis + metadata + processed`로 재구성
   - 여기서도 ingestion/preprocess/Steam fetch/LLM 분류는 호출되지 않음

---

## 5) LLM 사용 지점 총정리

모델 기본값: 모두 `OPENAI_MODEL` (기본 `gpt-4o-mini`)

1. 전처리 fallback 분류  
파일: `services/llm_classifier.py`  
경로: 오프라인만  
역할: ambiguous 리뷰 include/exclude + tags/theme 보조

2. 리포트 plan/display 작성  
파일: `services/report_writer_llm.py`  
경로: 오프라인 리포트 생성 시  
역할: report_plan + section-wise report_display

3. evidence snippet 압축  
파일: `services/evidence_snippet_llm.py`  
경로: 오프라인 리포트 생성 시  
역할: 1~4문장 가독 스니펫 재작성

4. 최종 한국어 교정  
파일: `services/korean_report_proofreader.py`  
경로: 오프라인 리포트 생성 시  
역할: 조사/문법/띄어쓰기 교정 (규칙+LLM hybrid)

5. evidence relevance judge (옵션)  
파일: `services/evidence_relevance_judge.py`  
경로: 오프라인 리포트 생성 시  
역할: 블록-스니펫 적합도 재판정  
기본값: `USE_LLM_EVIDENCE_JUDGE=false`

---

## 6) 환경변수/플래그 맵

### 6.1 공통 OpenAI

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (기본 `gpt-4o-mini`)

### 6.2 리포트 LLM 토글

- `USE_LLM_REPORT_WRITER` (기본 true)
- `USE_LLM_EVIDENCE_COMPRESSION` (기본 true)
- `USE_LLM_REPORT_PROOFREAD` (기본 true)
- `USE_LLM_EVIDENCE_JUDGE` (기본 false)

### 6.3 judge 세부

- `EVIDENCE_JUDGE_MAX_PER_BLOCK` (기본 8)
- `EVIDENCE_JUDGE_MAX_TOTAL` (기본 32)
- `EVIDENCE_JUDGE_MIN_CONFIDENCE` (기본 0.65)
- `EVIDENCE_JUDGE_TIMEOUT_SECONDS` (기본 8)
- `EVIDENCE_JUDGE_RETRY_LIMIT` (기본 1)

### 6.4 proofreader 세부

- `REPORT_PROOFREAD_MAX_LLM_TEXTS` (기본 24)

---

## 7) 프론트엔드 소비 레이어

기준 파일: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`

- `/api/games`에서 `report_ready=true` 게임만 선택 목록 노출
- `/api/games/{appid}/report`만 호출하여 리포트 렌더
- UI 섹션:
  - Hero(게임명, 배지, 헤드라인)
  - Decision(타이밍/현재상태/최종추천)
  - Fit(good_for/not_good_for)
  - Strength vs Risk
  - Evidence(강점 근거/리스크 근거)
- evidence 렌더링 시 `evidence_full_text` 우선 사용
- CSS 상 evidence 카드 line-clamp 없음 (전체 텍스트 표시 방향)

---

## 8) 품질/운영 보조 스크립트

1. 오프라인 실행  
`scripts/run_offline_pipeline.py`

- `.env` 자동 로드
- precheck 로그 출력(키 존재/모델명)

2. 배치 품질 리포트  
`scripts/batch_quality_report.py`

- 코호트별 `unclassified`, `canonical_theme_missing`, `ambiguity` 집계
- JSON + Markdown 리포트 동시 출력

3. 정규화 게이트  
`scripts/check_normalization_gate.py`

- 조건:
  - `included_drop_rate <= 0.10`
  - `unc_ratio_delta < 0`
- 실패 시 rollback required

---

## 9) 현재 데이터 상태 점검 (실측)

`data/report`를 확인한 결과, 리포트 버전이 혼재되어 있다.

- `2456740`, `1174180`: 구형 `v3` 산출물 흔적
- `1245620`, `413150`, `578080`: `v4-planned-sections`

의미:

- 온라인 `load_report()`는 v3를 유효 스키마로 보지 않으면 snapshot 기반 재구성으로 대응 가능
- 하지만 운영 일관성을 위해 모든 데모 게임을 v4로 재생성하는 것이 안전

---

## 10) 설계상 강점과 한계

### 강점

- 온라인 경로 완전 read-only화
- LLM을 보조/선택적 레이어로 분리
- 파일 기반 스냅샷으로 재현성과 디버깅 용이
- evidence 구조가 강점/리스크 분리되어 구매 판단 UX에 맞음

### 한계

- 파일 저장소 기반이라 동시성/이력관리 한계 존재
- 일부 리포트 버전 혼재(v3/v4)
- `USE_LLM_EVIDENCE_JUDGE` ON 시 품질 이득이 게임별로 불안정할 수 있음
- 리뷰 샘플 대표성(표본 편향) 자체는 본질적으로 남음

---

## 11) 코드 기준 실행 절차 요약

### 오프라인 수집/분석/리포트 생성

```bash
python apps/review-insights/scripts/run_offline_pipeline.py ^
  --appid 578080 ^
  --review-pages all ^
  --use-llm-fallback
```

### 서버 실행

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

### 사용자 확인

- 브라우저: `http://localhost:8000`
- API: `/api/games`, `/api/games/{appid}/report`

---

## 12) 최종 판단

현재 구현은 목표한 “오프라인 분석 + 온라인 조회 전용” 구조를 코드 레벨에서 대부분 충족한다.  
추가 안정화를 위해서는 **데모 코호트 전체를 v4 리포트로 일괄 재생성**하고, `evidence judge`는 게임별 A/B 근거가 있을 때만 선택 적용하는 운영 정책이 적합하다.

