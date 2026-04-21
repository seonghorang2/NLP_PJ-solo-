# Steam 리뷰 기반 구매 의사결정 리포트 시스템 리서치 (최신 코드 기준)

작성일: 2026-04-16  
기준 브랜치: 현재 워크스페이스 코드 전체  
대상 독자: 프로젝트를 처음 보는 개발자/기획자/운영자

---

## 1. 이 문서의 목적

이 문서는 `apps/review-insights`의 **현재 실제 동작 구조**를 코드 기준으로 설명한다.  
핵심 목표는 아래 2가지를 명확히 이해하는 것이다.

1. 오프라인 파이프라인에서 무엇이 실행되고 무엇이 저장되는가  
2. 온라인(사용자 조회) 경로에서 무엇이 절대 실행되지 않는가

---

## 2. 한 줄 정의

이 시스템은 Steam 리뷰를 **오프라인에서 미리 수집/분석/리포트화**해두고,  
사용자는 저장된 결과를 **즉시 조회**하는 구매 의사결정 리포트 서비스다.

---

## 3. 전체 아키텍처 (요약)

```text
[운영자 수동 실행]
  -> offline_pipeline.run_offline_pipeline_for_appid()
     -> Steam 리뷰/메타 수집
     -> 결정론 전처리 + 분류
     -> 분석 집계
     -> (선택) LLM 리포트 재료 정제
     -> 리포트 생성(결정론 + 선택 LLM 보강)
     -> raw/processed/analysis/metadata/report 저장

[사용자 요청]
  -> GET /api/games/{appid}/report
     -> 저장된 report 읽기
     -> (report 없을 때만) 저장된 analysis/processed 기반 즉시 조립
     -> 응답 반환
```

---

## 4. 저장소 핵심 구조

- 백엔드 엔트리: `apps/review-insights/backend/app.py`
- API 라우트: `apps/review-insights/backend/api/routes.py`
- 오프라인 파이프라인: `apps/review-insights/backend/pipeline/offline_pipeline.py`
- 분석 계층:
  - `analysis/preprocess.py`
  - `analysis/rules.py`
  - `analysis/categorize.py`
  - `analysis/themes.py`, `analysis/trends.py`, `analysis/summarize.py`
- 리포트 계층:
  - `services/report_view.py`
  - `services/report_writer_llm.py`
  - `services/report_material_refiner.py`
  - `services/evidence_judge_llm.py`
  - `services/korean_report_proofreader.py`
- Steam 연동: `services/steam_reviews.py`
- 저장소: `storage/file_store.py`
- 프론트: `frontend/src/main.jsx`, `frontend/src/App.jsx`, `frontend/src/pages/ReportPage.jsx`, `frontend/src/styles/report.css`
- 실행 스크립트: `scripts/run_offline_pipeline.py`

---

## 5. 데이터 아티팩트와 파일 저장 규칙

저장 루트: `apps/review-insights/data`

- `raw/`: Steam 원문 리뷰(JSON 배열)
- `processed/`: 전처리 + 규칙 판정 결과
- `analysis/`: 집계 결과 + 실행 메타 + LLM 통계
- `metadata/`: 게임 메타데이터
- `report/`: 사용자 렌더용 최종 리포트 JSON
- `catalog/demo_games.json`: 사용자 노출 허용 게임 목록

파일명 규칙:
- 기본: `appid(게임명).json`
- `FileStore`가 최신 수정 파일을 우선 조회

---

## 6. 오프라인 파이프라인 상세 동작

기준 함수: `run_offline_pipeline_for_appid()`  
파일: `backend/pipeline/offline_pipeline.py`

### 6.1 입력 파라미터

- `appid` (필수)
- `review_pages`: `"all"` 또는 `1~200`
- `use_llm_fallback` (현재 의미: 리포트 재료 LLM 정제 활성화)
- `max_llm_reviews` 기본 `50`
- `llm_timeout_seconds` 기본 `20`
- `llm_retry_limit` 기본 `2`
- `llm_min_confidence` 기본 `0.70`

### 6.2 수집 단계

- `fetch_steam_reviews()` 호출
  - 기본 `language="koreana"`
  - 기본 `filter_type="recent"` (최신순)
  - `review_pages="all"`은 내부 상한 `200페이지`
- `fetch_steam_game_metadata()` 호출

### 6.3 결정론 전처리

파일: `analysis/preprocess.py`, `analysis/rules.py`

순서:
1. `clean_markup_text()`로 HTML/BBCode 제거
2. `normalize_text()` 정규화
3. `hangul_ratio` 계산
4. 저품질/욕설-only/비한국어 제외 판정
5. 포함 리뷰는 `extract_category_tags()` 멀티라벨 태깅
6. `rule_confidence`, `ambiguity_flags`, `final_decision` 기록

핵심 제외 조건:
- `is_low_quality_review == True`
- `is_profanity_only_review == True`
- `hangul_ratio < 0.20`

### 6.4 분석 집계

파일: `services/analysis_service.py`

- `enrich_processed_reviews()`로 `canonical_theme` 보강
- 카테고리별 `IssueSignal` 생성
  - `mention_count`
  - `negative_ratio`
  - `recent_trend`
  - `experienced_player_share`
  - `themes`, `sample_reviews`
- `AnalysisResult` 생성 및 summary/warnings 포함

### 6.5 리포트 재료 LLM 정제 (선택)

파일: `services/report_material_refiner.py`

현재 구조:
- 전처리 fallback이 아니라 **분석 이후 단계**에서 동작
- `included_in_analysis=true` 리뷰 중 유틸리티 상위 최대 `50`개 선별
- 긍정/부정 균형 우선, 부족 시 나머지로 채움
- LLM 출력:
  - `refined_text` (1~4문장)
  - `stance`
  - `confidence`
- 실패/저신뢰 시 deterministic fallback 텍스트 사용
- 캐시/timeout/retry 적용

### 6.6 리포트 생성

파일: `services/report_view.py`

생성 계약:
- `report_plan`
- `report_display`
- `evidence_sections`

출력 전 후처리:
- 유/무료 게임 추천 라벨 변환
- 한국어 문법/조사 교정(rule + 선택 LLM)
- 금지 라벨 치환(분류형 용어 -> 경험형 문장)
- legacy flat 필드 병행 제공

### 6.7 저장

파이프라인 1회 실행 시 아래를 모두 저장:
- `raw`, `processed`, `analysis`, `metadata`, `report`

---

## 7. 온라인 API (사용자 조회) 상세

파일: `backend/api/routes.py`

사용자 경로:
- `GET /api/health`
- `GET /api/games`
- `GET /api/games/{appid}/report`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`
- `GET /api/games/{appid}/raw` (디버그)
- `GET /api/games/{appid}/processed` (디버그)

운영 경로:
- `POST /api/admin/ingest` (수동 파이프라인 실행)

중요 경계:
- 사용자 경로는 demo catalog allow-list(appid) 검사 후 파일 조회만 수행
- 사용자 경로에서 Steam fetch/전처리/분석/LLM 호출 없음

예외:
- `/report`에서 저장된 report가 없으면, 저장된 `analysis + processed`로 즉시 report 조립 가능
- 이 fallback도 네트워크 fetch/재분석 없이 로컬 스냅샷 기반

---

## 8. LLM 사용 지점 정리 (현재 코드 기준)

### 8.1 사용 중

1. `report_material_refiner.py`
- 용도: 리포트 재료 리뷰 정제
- 위치: 오프라인 파이프라인

2. `report_writer_llm.py`
- 용도: plan/display 섹션 생성 보강
- 위치: report 생성 단계
- 플래그: `USE_LLM_REPORT_WRITER` (기본 true)

3. `evidence_judge_llm.py`
- 용도: 근거 후보 중 stance/theme 일치 항목 선택(judge-only)
- 플래그: `USE_LLM_EVIDENCE_JUDGE` (기본 false)

4. `korean_report_proofreader.py`
- 용도: 최종 한국어 교정
- 플래그: `USE_LLM_REPORT_PROOFREAD` (기본 true)

### 8.2 코드에 있으나 현재 파이프라인 미연결

- `analysis/llm_fallback.py`
- `services/llm_classifier.py`

설명:
- 이 모듈은 “전처리 애매 리뷰 fallback” 구조용이며,
- 현재 `offline_pipeline.py`는 해당 경로를 호출하지 않고 `report_material_refiner`를 사용한다.

---

## 9. 리포트 생성 내부 로직 핵심

파일: `services/report_view.py`

### 9.1 합의 신호(consenus) 구성

- `analysis.issue_signals`를 순회해 `consensus_aspects` 생성
- 최소 언급량 기준:
  - high: `max(12, included_count*0.06)`
  - medium: `max(6, included_count*0.03)`
- aspect별:
  - `mention_count`, `negative_ratio`, `recent_trend`
  - `themes`, `tone`
  - `evidence_group`(positive/negative 샘플)

### 9.2 결정론 리포트 seed

- 강점/리스크 선택
- 추천(`buy_now`, `buy_on_sale`, `wait`, `not_recommended`) 결정
- 유/무료 맵핑 반영
- `good_for`, `not_good_for`, `recent_state` 생성

### 9.3 근거 블록 생성 (3단계 게이트)

- Stage 1: strict (stance + theme 일치)
- Stage 2: relaxed (stance 일치 + 재료 확장)
- Stage 3: guaranteed_fill (빈 섹션 방지)

각 블록 구조:
- `title`
- `why_it_matters`
- `stance`
- `mention_count`
- `evidence_snippets` (2~3개)
- `evidence_quality_level` (`strict|relaxed|guaranteed_fill`)

### 9.4 근거 후보 최종 선별

- 후보 최대 8개 랭킹
- 옵션으로 LLM judge 적용 시 인덱스 재선택
- 실패 시 규칙 랭킹 fallback
- 최소 2개 스니펫 보장

---

## 10. 프론트 렌더링 구조

파일:
- `frontend/src/pages/ReportPage.jsx`
- `frontend/src/components/*`
- `frontend/src/api/reportApi.js`
- `frontend/src/utils/reportMappers.js`

흐름:
1. `fetchDemoGames()`로 `/api/games` 호출 후 `report_ready` 게임만 노출
2. 선택 appid 기준 `fetchReport()`로 `/api/games/{appid}/report` 호출
3. `report_display` + `evidence_sections`를 React 컴포넌트 트리로 렌더

렌더 원칙:
- dashboard형 수치판보다 구매결정 카드 중심
- 근거는 strengths/risks 분리
- React 문자열 렌더링으로 HTML 인젝션 경로 차단
- 긴 스니펫은 줄바꿈 표시를 유지하되 텍스트 자체는 최대한 보존

---

## 11. 실행 방법 (운영/시연)

### 11.1 오프라인 생성

```bash
python apps/review-insights/scripts/run_offline_pipeline.py --appid 578080 --review-pages all --use-llm-fallback
```

### 11.2 서버 실행

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

브라우저: `http://localhost:8000`

---

## 12. 품질 게이트/검증 도구

- 배치 품질 리포트: `scripts/batch_quality_report.py`
- 정규화 게이트: `scripts/check_normalization_gate.py`
- 리포트 릴리즈 게이트: `scripts/check_report_release_gate.py`
  - 출력: `data/reports/report_release_gate.json/.md`

테스트 스위트:
- `apps/review-insights/tests/*`
- 전처리/분류/분석/API/리포트/게이트 테스트 포함

---

## 13. 현재 구조의 장점과 리스크

### 장점

- 사용자 요청이 매우 가벼움(읽기 전용)
- 외부 API 지연/실패가 사용자 응답에 직접 전파되지 않음
- LLM 비용을 오프라인에서 상한 관리 가능
- 결과 아티팩트가 파일로 남아 디버깅 쉬움

### 리스크/주의점

- 파일 저장소 기반이라 대규모 동시 운영에는 한계
- 문서 일부(전처리 LLM fallback 설명)와 실제 코드가 부분 불일치할 수 있음
- LLM 다단 사용 시 실행 시간/비용 관리 필요
- 카테고리 사전/금지라벨 사전의 지속 보강이 품질 핵심

---

## 14. 결론 (현재 상태 한 줄)

현재 시스템은 **오프라인 선분석 + 온라인 읽기 전용** 경계를 잘 지키는 구조이며,  
LLM은 전면 분류기가 아니라 **리포트 품질 보강 계층**으로 제한되어 운영되고 있다.
