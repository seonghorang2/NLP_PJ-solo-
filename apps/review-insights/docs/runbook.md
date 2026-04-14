# review-insights Runbook

## 1. 목적

데모 운영형 구조에서 배치 실행, refresh check, 수동 재분석 절차를 정의한다.

---

## 2. 운영 원칙

- 사용자 경로는 저장된 snapshot 조회만 수행한다.
- 운영 경로에서만 ingest/분석을 수행한다.
- 자동 재분석은 사용하지 않는다.
- 데모 코호트(`data/catalog/demo_games.json`)에 포함된 게임만 지원한다.

---

## 3. 단계별 운영 흐름

### 3.1 초기 적재

1. 코호트 게임 목록 확정
2. 게임별 ingest 수동 실행
3. `raw/processed/analysis/metadata` 파일 생성 확인

### 3.2 refresh check

1. 현재 리뷰 수 조회
2. 마지막 분석 리뷰 수 조회
3. `delta = current_review_count - last_review_count` 계산
4. `delta >= n` -> `needs_refresh`
5. `delta < n` -> `up_to_date`

### 3.3 수동 재분석

1. `needs_refresh` 게임 선택
2. ingest 수동 실행
3. snapshot 메타(`generated_at`, `source_review_count`) 갱신 확인

---

## 4. LLM 운영 규칙

### 4.1 호출 게이트

- 의미 신호 AND 불확실성 신호를 모두 만족해야 호출
- 단일 조건 호출 금지

### 4.2 호출 금지 구간

- 극저 한글 비율
- 명백한 저품질
- 명백한 욕설-only
- 빈/기호-only

### 4.3 안전장치

- 배치당 `max_llm_reviews`
- 호출 timeout
- retry max 2
- schema invalid 시 rule fallback
- 동일 텍스트 캐시

---

## 5. 서버 실행

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

---

## 6. API 경로

### 6.1 사용자 경로 (read-only)

- `GET /api/games`
- `GET /api/games/{appid}/report`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`

주의:

- 사용자 경로는 Steam API 호출/ingestion/preprocess/LLM 분석을 수행하지 않는다.
- `POST /api/ingest` 경로는 제거되었고, 운영 실행은 `POST /api/admin/ingest`만 사용한다.

### 6.2 운영 경로 (수동)

- `POST /api/admin/ingest`

예시:

```bash
curl -X POST http://localhost:8000/api/admin/ingest \
  -H "Content-Type: application/json" \
  -d "{\"appid\":2456740,\"review_pages\":\"all\",\"use_llm_fallback\":true}"
```

---

## 7. 품질 점검

```bash
python apps/review-insights/scripts/batch_quality_report.py --appids 2456740 1049590
```

출력:

- `apps/review-insights/data/reports/batch_quality_report.json`
- `apps/review-insights/data/reports/batch_quality_report.md`

---

## 8. 비범위

- 자동 스케줄러 기반 재분석
- 자동 트리거 기반 ingest 실행
- 게임 비교 화면/API
