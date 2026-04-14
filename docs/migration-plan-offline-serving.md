# Migration Plan: 온디맨드 파이프라인 -> 오프라인 분석 + 온라인 조회 전용 서빙

## 0. 목적과 고정 제약

이 문서는 현재 온디맨드 처리 구조를 다음 목표 구조로 이행하기 위한 마이그레이션 계획이다.

- 오프라인 분석 파이프라인(수집/전처리/분석/리포트 생성)
- 온라인 조회 전용 서빙(read-only report serving)

### 고정 제약 (반드시 준수)

1. 사용자 요청 경로에서 아래 동작은 절대 실행하지 않는다.
- Steam API fetch
- ingestion
- preprocessing
- LLM review analysis

2. LLM은 오프라인 전처리 파이프라인의 fallback에서만 사용한다.
3. 데모 범위는 사전 정의된 게임 코호트만 허용한다.
4. 오프라인 파이프라인 실행은 수동 트리거만 허용한다.
5. 큐/워커/스케줄러 같은 프로덕션 대규모 인프라는 도입하지 않는다.

---

## 1. 현재 플로우 요약 (Current Flow)

현재는 사용자 요청이 수집/분석을 직접 유발한다.

1. 프론트엔드 submit -> `POST /api/ingest`
2. `routes.py::ingest_reviews_payload()`
3. `steam_payload` 미전달 시 Steam fetch 수행
- `fetch_steam_reviews()`
- `fetch_steam_game_metadata()`
4. 이어서 ingestion + preprocessing + analysis + 저장 수행
- `normalize_steam_reviews()`
- `run_and_persist_analysis()`
5. 저장 후 프론트에서 조회 API 연속 호출
- `GET /api/games/{appid}/analysis|raw|processed`

핵심 문제:

- 사용자 요청 경로가 네트워크 fetch와 분석 지연을 직접 부담
- 온라인/오프라인 책임 분리 실패

---

## 2. 사용자 경로 트리거 전수 점검

## 2.1 Steam API fetch를 유발하는 사용자 경로

- `frontend/app.js` -> `fetch("/api/ingest", ...)`
- `backend/api/routes.py::ingest_reviews_payload()`
  - `fetch_steam_reviews()`
  - `fetch_steam_game_metadata()`

## 2.2 ingestion을 유발하는 사용자 경로

- 동일 `/api/ingest` 경로에서 normalize + persist 실행

## 2.3 preprocessing/analysis를 유발하는 사용자 경로

- `run_and_persist_analysis()` -> `analyze_reviews()` -> `preprocess_reviews()`

## 2.4 LLM review analysis를 유발하는 사용자 경로

- 현재 코드 기준 실제 LLM 호출은 없음(필드만 존재)
- 하지만 구조상 `/api/ingest` 경로에 LLM 연결 시 사용자 경로로 누수될 위험이 존재

결론:

- 사용자 요청이 Steam fetch/ingestion/preprocess/analysis를 트리거하는 구조가 현재 존재함
- 목표 구조에서는 이를 0으로 만들어야 함

---

## 3. 목표 아키텍처 요약 (Target Flow)

## 3.1 Offline Pipeline (운영 경로)

1. 코호트 게임 선택
2. 리뷰/메타데이터 수집
3. 결정론 전처리
4. 애매한 subset에 한해 LLM fallback
5. 최종 병합/집계
6. 스냅샷 저장
7. refresh check 결과 저장

## 3.2 Online Serving (사용자 경로)

1. 사용자 appid 선택
2. 저장된 스냅샷 읽기
3. read-only 리포트 응답

온라인 경로 불변 규칙:

- fetch 없음
- ingestion 없음
- preprocessing 없음
- LLM 없음

---

## 4. 데이터 흐름도 (텍스트)

```text
[Admin Manual Trigger]
   -> [Offline Ingest Entry]
      -> Steam Fetch (reviews + metadata)
      -> Deterministic Preprocess
      -> Ambiguity Detection
      -> Selective LLM Fallback (offline only)
      -> Final Merge + Aggregation
      -> Snapshot Write
      -> Refresh Status Write

[User Request]
   -> [Online Read API]
      -> Snapshot Read Only
      -> Report Response
```

---

## 5. 파이프라인 엔트리포인트 정의

## 5.1 오프라인 엔트리포인트 (허용)

- 운영용 API(수동): 예 `POST /api/admin/ingest`
- 운영용 refresh check API/스크립트(수동): 예 `GET /api/admin/refresh-check`, `POST /api/admin/refresh-run`
- 로컬 운영 스크립트 실행

## 5.2 온라인 엔트리포인트 (허용)

- `GET /api/games`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`
- `GET /api/games/{appid}/report` (권장)

## 5.3 온라인 엔트리포인트 (금지)

- `/api/ingest` 직접 호출
- Steam fetch를 유발하는 모든 경로
- 분석 실행을 유발하는 모든 경로

---

## 6. 업데이트된 API 구조

## 6.1 사용자용(read-only)

- `GET /api/games`  
  - 데모 코호트 내 게임 목록/상태
- `GET /api/games/{appid}/report`  
  - 리포트 뷰 모델(권장)
- `GET /api/games/{appid}/analysis`  
  - 분석 스냅샷 원문(디버그/내부)
- `GET /api/games/{appid}/metadata`

## 6.2 운영용(manual only)

- `POST /api/admin/ingest`  
  - 단일/다중 appid 수동 ingest + 분석
- `GET /api/admin/refresh-check?appid=...`
  - `delta = current_review_count - last_review_count`
  - 상태: `up_to_date | needs_refresh`
- `POST /api/admin/refresh-run`
  - `needs_refresh` 대상 수동 재분석 실행

주의:

- 기존 `/api/ingest`는 제거하고 `/api/admin/ingest`만 사용

---

## 7. 제거/격리 대상 동작 목록 (Removed Behaviors)

아래 동작은 사용자 경로에서 제거 또는 격리한다.

1. 프론트 submit 시 `/api/ingest` 호출
2. 사용자 요청 시 Steam 리뷰 fetch
3. 사용자 요청 시 metadata fetch
4. 사용자 요청 시 전처리/분석 실행
5. 사용자 요청 시 LLM fallback 실행
6. 사용자 요청 시 raw/processed 재생성

---

## 8. 파일별 영향도

| 파일 | 현재 역할 | 마이그레이션 영향 |
|---|---|---|
| `apps/review-insights/frontend/app.js` | submit -> `/api/ingest` | 사용자 경로에서 ingest 호출 제거, 조회 API만 사용 |
| `apps/review-insights/frontend/index.html` | ingest 중심 UI | 조회 중심 UI로 전환 |
| `apps/review-insights/backend/api/routes.py` | ingest + 조회 혼재 | 운영/조회 라우트 분리, 온라인 경로 read-only 고정 |
| `apps/review-insights/backend/services/steam_reviews.py` | fetch 유틸 | 오프라인 경로 전용으로 사용 범위 제한 |
| `apps/review-insights/backend/services/analysis_service.py` | 즉시 분석 실행 | 오프라인 실행 전용으로 격리 |
| `apps/review-insights/backend/storage/file_store.py` | raw/processed/analysis 저장 | snapshot/refresh 메타 저장 확장 |
| `apps/review-insights/backend/models/schemas.py` | 분석 모델 | snapshot/refresh/trace 필드 확장 |
| `apps/review-insights/scripts/*` | 품질 리포트 위주 | 코호트 ingest/refresh check/manual refresh 보강 |
| `apps/review-insights/tests/test_api_flow.py` | ingest 중심 | 사용자 read-only 테스트 중심으로 재편 |

---

## 9. 저장소/스키마 영향

## 9.1 저장소

유지:

- `data/raw`
- `data/processed`
- `data/analysis`
- `data/metadata`

추가 권장:

- `data/catalog/demo_games.json`
- `data/ops/refresh_status.json`
- `data/pipeline_runs/*.json`

## 9.2 스키마

### Analysis Snapshot 필수 메타

- `generated_at`
- `source_review_count`
- `pipeline_run_id`
- `refresh_status`
- `refresh_threshold_n`

### Processed Review trace 확장

- `rule_confidence`
- `llm_confidence`
- `final_decision`
- `final_decision_source`

### Demo Games Catalog 필수

- `appid`
- `name`
- `enabled_for_demo`
- `refresh_threshold_n`
- `last_review_count`
- `last_ingested_at`
- `last_analyzed_at`

---

## 10. 단계별 마이그레이션 계획

### Phase 0. 경계 고정

- 사용자 경로 금지 동작을 문서/테스트 기준으로 고정
- 라우트 책임(online read-only vs offline admin) 정의 확정

### Phase 1. 사용자 경로 read-only 전환

- 프론트 `/api/ingest` 호출 제거
- 사용자 요청은 `GET /api/games`, `GET /api/games/{appid}/report` 중심으로 전환
- snapshot/report 미존재 상태 처리(`report not ready`)
- demo catalog allow-list 외 appid 차단

### Phase 2. 오프라인 엔트리포인트 확립

- 운영용 ingest 엔트리포인트 분리
- 코호트 초기 적재 완료
- 스냅샷 메타 기록 시작

### Phase 3. refresh check + 수동 재분석

- delta 계산 및 `needs_refresh` 판정 저장
- 수동 `refresh-run` 실행 경로 반영
- `delta < n`이면 스킵 + 기존 snapshot 유지

### Phase 4. LLM 오프라인 전용 통제

- LLM fallback 오프라인 경로에만 연결
- 사용자 경로 LLM 실행 방지 테스트 추가
- 게이트/timeout/retry/caching 정책 적용

### Phase 5. 안정화

- 사용자 API 성능 검증(read-only)
- 운영 절차/runbook 검증
- 롤백 플래그 확인

---

## 11. 리스크

1. snapshot 미적재 상태에서 사용자 조회 실패
2. 오프라인 실행 실패로 freshness 저하
3. 경계 분리 누락으로 사용자 경로 지연 재발
4. LLM 통제 실패 시 비용/시간 급증

---

## 12. 롤백 노트

1. `/api/ingest`는 제거 상태를 유지하고, 운영 실행은 `/api/admin/ingest`만 사용한다.
2. 사용자 경로 롤백은 허용하지 않고 read-only 원칙을 고정한다.
3. 신규 리포트 필드 문제 시 기존 `analysis` 기반 경량 변환 모드로 서빙을 유지한다.
4. refresh check 실패 시 마지막 정상 snapshot을 계속 서빙한다.

---

## 13. 비목표(이번 데모에서 하지 않음)

- 자동 스케줄러
- 메시지 큐/워커
- 분산 배치 인프라
- 전 게임 카탈로그 자동 확장
