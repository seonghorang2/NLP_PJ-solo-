# review-insights 앱 상세 구조 설계

## 1. 목적

이 문서는 `apps/review-insights/` 앱의 디렉터리 구조와 책임 분리를 상세하게 정의한다.

이 앱은 다음 MVP만 담당한다.

- 1개 또는 2개 게임 선택
- Steam 리뷰 수집
- 전처리
- 카테고리 분류
- 키워드/테마 추출
- 트렌드 분석
- 요약 생성
- 간단한 내부 대시보드

추천 시스템, 대규모 전체 리뷰 분석, 범용 공통 플랫폼 역할은 이 앱의 책임이 아니다.

---

## 2. 권장 구조

```text
apps/
  review-insights/
    backend/
      app.py
      api/
        routes.py
      services/
        steam_reviews.py
        analysis_service.py
      analysis/
        preprocess.py
        rules.py
        llm_preprocess.py
        categorize.py
        themes.py
        trends.py
        summarize.py
      storage/
        file_store.py
      models/
        schemas.py

    frontend/
      index.html
      app.js
      styles.css

    data/
      raw/
      processed/
      analysis/

    tests/
      test_preprocess.py
      test_categorize.py
      test_trends.py

    docs/
      runbook.md
      api.md
```

---

## 3. 디렉터리별 책임

### `backend/`

앱의 서버 측 진입점과 기능 구현을 둔다.

### `backend/api/`

HTTP 엔드포인트만 둔다.

책임:

- 요청/응답 연결
- 입력 검증
- 서비스 호출

비책임:

- 분석 로직 직접 구현
- 파일 저장 직접 구현

### `backend/services/`

외부 API 호출과 파이프라인 조합을 담당한다.

책임:

- Steam 리뷰 수집
- ingestion + preprocessing + analysis orchestration

비책임:

- 세부 텍스트 규칙 구현

### `backend/analysis/`

결정론적 코어 분석 로직과 제한적 LLM fallback 로직을 둔다.

책임:

- 전처리
- 애매한 리뷰 선별
- 선택적 LLM 보조 판정
- 멀티 라벨 카테고리 분류
- 키워드 및 canonical theme 추출
- 트렌드 계산
- 주요 이슈 신호 집계
- 요약 생성

이 앱은 단일 우선순위 점수를 계산하지 않는다.
대신 카테고리별 주요 이슈 신호를 집계해 사용자가 직접 판단할 수 있도록 한다.

### `backend/storage/`

파일 저장과 조회를 담당한다.

책임:

- raw/processed/analysis JSON 저장
- 경로 생성
- 로드/조회

### `backend/models/`

요청/응답 및 내부 레코드 구조를 명시한다.

권장 필드:

- `ambiguity_flags`
- `rule_decision`
- `llm_invoked`
- `llm_decision`
- `llm_confidence`
- `final_decision_source`
- `category_tags`
- `primary_category`
- `canonical_theme`
- `playtime_at_review_hours`
- `num_reviews`

---

## 4. 데이터 디렉터리 설계

```text
apps/review-insights/data/
  raw/
  processed/
  analysis/
```

### `raw/`

- Steam에서 수집한 원본 리뷰 정규화 결과 저장
- 주요 이슈 신호 해석에 필요한 작성자 메타데이터 저장

### `processed/`

- 리뷰별 전처리 결과 저장
- 필터링된 리뷰도 메타데이터와 함께 보존
- 규칙 기반 판정, LLM 판정, 최종 판정 흔적 보존

### `analysis/`

- 집계 결과
- 카테고리 분포
- 트렌드
- 요약

---

## 5. 테스트 구조

```text
apps/review-insights/tests/
  test_preprocess.py
  test_categorize.py
  test_trends.py
```

테스트는 결정론적 핵심 규칙에 집중한다.

- 한국어 판별
- 저품질 제외
- 욕설-only 제외
- 애매한 리뷰 선별
- LLM 호출 여부 결정
- 멀티 라벨 카테고리 태깅
- 트렌드 스파이크 감지
- 주요 이슈 신호 집계

---

## 6. 문서 구조

```text
apps/review-insights/docs/
  runbook.md
  api.md
```

### `runbook.md`

- 실행 방법
- 데이터 저장 위치
- 로컬 검증 방법
- 트러블슈팅

### `api.md`

- 엔드포인트 목록
- 요청/응답 예시
- 필드 설명

분석 규칙 기준 문서:

- `docs/analysis-policy.md`

---

## 7. 구현 순서에 맞춘 파일 생성 계획

### 1단계

- `backend/app.py`
- `backend/api/routes.py`
- `backend/models/schemas.py`

### 2단계

- `backend/storage/file_store.py`
- `backend/services/steam_reviews.py`

### 3단계

- `backend/analysis/preprocess.py`
- `backend/analysis/rules.py`
- `backend/analysis/llm_preprocess.py`

### 4단계

- `backend/analysis/categorize.py`
- `backend/analysis/themes.py`
- `backend/analysis/trends.py`
- `backend/analysis/summarize.py`
- `backend/services/analysis_service.py`

### 5단계

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`

### 6단계

- `tests/test_preprocess.py`
- `tests/test_categorize.py`
- `tests/test_trends.py`

### 7단계

- `apps/review-insights/docs/runbook.md`
- `apps/review-insights/docs/api.md`

참고:

- 분석 규칙의 기준 문서는 루트 `docs/analysis-policy.md`다.

---

## 8. 이 구조에서 의도적으로 하지 않는 것

- 추천 시스템용 공통 추상화 추가
- 다른 앱을 고려한 범용 분석 프레임워크 추가
- DB, 큐, 배치 시스템 도입
- 공통 프론트 컴포넌트 라이브러리 구축
- 다국어 분석 지원
- 전처리 전체를 LLM에 위임하는 블랙박스 구조

이것들은 현재 앱의 MVP 범위를 벗어난다.

---

## 9. 결론

`review-insights` 앱은 독립적인 제품으로 취급하고, 구현과 데이터와 문서를 앱 내부에 모으는 것이 가장 단순하다.

이 구조는 다음 장점이 있다.

- 팀 간 충돌이 적다.
- 제품 경계가 명확하다.
- 리뷰 가능한 작은 단위로 구현하기 쉽다.
- 나중에 필요한 공통화만 선택적으로 추출할 수 있다.
