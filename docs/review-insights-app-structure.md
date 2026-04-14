# review-insights 앱 구조

## 1. 서비스 정의

`review-insights`는 단일 게임 리뷰 기반 인사이트 리포트 서비스다.  
사용자 요청 시 저장된 분석 스냅샷을 조회해 리포트를 반환한다.

---

## 2. 디렉터리 구조

```text
apps/review-insights/
  backend/
    api/
    analysis/
    models/
    services/
    storage/
  frontend/
  data/
    raw/
    processed/
    analysis/
    metadata/
  docs/
  tests/
```

---

## 3. 계층 책임

- `api`: 조회/운영 엔드포인트
- `services`: 수집 및 분석 orchestration
- `analysis`: 규칙 기반 분석 코어
- `storage`: 스냅샷 저장소 접근
- `frontend`: 리포트 화면

---

## 4. 실행 경로

### 사용자 경로

1. appid 선택
2. analysis snapshot 조회
3. 리포트 렌더링

### 운영 경로

1. refresh check 실행
2. `needs_refresh` 판정
3. 수동 재분석 실행
4. snapshot 갱신

---

## 5. 데모 운영 조건

- 데모 코호트 게임만 지원한다.
- 코호트 외 게임은 분석/조회 대상에서 제외한다.
- 자동 트리거/자동 재분석은 구현하지 않는다.
- refresh 판단 로직은 구현하되 실행은 수동으로 유지한다.

---

## 6. 금지 사항

- 사용자 조회 경로 실시간 Steam 수집
- 사용자 조회 경로 실시간 LLM 호출
- 게임 비교 UI/API 추가
