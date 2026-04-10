# Steam 리뷰 인사이트 MVP 계획

## 1. 기준 문서 (Source of Truth)

이 계획은 `AGENTS.md`와 `steam-review-insights-spec.md`를 기준으로 작성한다.
강한 제품/엔지니어링 규칙은 `AGENTS.md`를 우선 기준으로 삼고, 이 문서는 구현 설계와 단계별 계획에 집중한다.

---

## 2. 현재 저장소 분석 (Current Repository Analysis)

초기 저장소 상태 분석은 구현 초기에만 유효한 정보이므로 이 계획서의 핵심 범위에서 제외한다.
이 문서는 현재 기준 구현 구조, 데이터 흐름, 정책, 단계별 작업 순서에 집중한다.

---

## 3. MVP 제품 목표 (MVP Product Goal)

다음 기능을 지원하는 Steam 내부용 리뷰 분석 도구를 구축한다.

- 1개 또는 2개 게임 분석
- Steam 리뷰 수집
- 결정론적 필터를 활용한 전처리
- 카테고리 태깅
- 키워드/테마 추출
- 트렌드 분석
- 요약 생성
- 단순한 내부 대시보드

### MVP 범위에서 제외되는 항목

- 로그인/인증
- 실시간 스트리밍
- 다국어 분석
- 대규모 ML 학습
- 추천 시스템
- 분산 워커 / 큐
- 로컬/내부 사용 범위를 넘는 수준의 운영 인프라 이슈

---

## 4. 아키텍처 개요 (Architecture Overview)

단순한 3계층 아키텍처를 사용함

1. 수집 + 분석 백엔드
2. 파일 기반 로컬 저장소
3. 경량 내부 대시보드 프론트엔드

### 4.1 상위 구조

```text
프론트엔드 대시보드
    |
    v
백엔드 API
    |
    +--> Steam 리뷰 수집기
    +--> 전처리기
    +--> 카테고리 / 테마 분석기
    +--> 트렌드 분석기
    +--> 요약 생성기
    |
    v
로컬 JSON 저장소
```

### 4.2 아키텍처 선택 이유

- 1~2개 게임 분석에는 충분
- 로직이 명시적이고 디버깅하기 쉬움
- 결정론적 분석을 요구하는 MVP 조건에 부합
- 데이터베이스나 운영 인프라에 대한 시기상조의 선택을 피할 수 있음

---

## 5. 저장소 구조 (Proposed Repository Structure)

이 저장소는 여러 Steam 관련 내부 제품이 공존할 수 있는 모노레포로 설계

핵심 원칙:

- 제품 단위로 디렉터리를 분리
- 현재 우리가 구현하는 서비스는 `review-insights` 앱으로 고립
- 다른 팀의 추천 시스템은 `game-recommendation` 앱으로 분리
- 공통화는 실제 중복이 확인되기 전까지 최소화

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
        llm_preprocess.py
        categorize.py
        themes.py
        trends.py
        summarize.py
        rules.py
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

  game-recommendation/
    backend/
    frontend/
    data/
    tests/
    docs/

shared/
  README.md

docs/
  architecture.md
  analysis-policy.md
  review-insights-app-structure.md
```

### 5.1 구조 설계 근거

- `apps/review-insights/`는 이번 MVP의 제품 경계를 나타낸다.
- `apps/game-recommendation/`는 다른 팀 서비스와의 충돌을 예방하기 위한 분리 공간이다.
- `services/`는 전체 흐름 조정과 외부 API 연동을 담당한다.
- `analysis/`는 결정론적인 리뷰 분석 로직을 담당한다.
- `storage/`는 파일 입출력을 분리하여 이후 저장 방식 변경 시 영향을 줄인다.
- `models/`는 데이터 구조를 명시적으로 유지한다.
- `frontend/`는 내부 도구 목적에 맞게 작고 단순하게 유지한다.
- `shared/`는 문서화된 공통 자산만 신중하게 수용한다.

---

## 6. 데이터 흐름 (Data Flow)

### 6.1 단일 게임 분석 흐름

1. 사용자가 대시보드에서 게임을 선택한다.
2. 프론트엔드가 `POST /api/ingest`를 호출한다.
3. 백엔드가 해당 `appid`의 Steam 리뷰를 가져온다.
4. 원본 리뷰를 변경 없이 `apps/review-insights/data/raw/`에 저장한다.
5. 각 리뷰에 대해 전처리를 수행한다.
6. 필터링된 리뷰도 메타데이터는 유지하되 분석에서는 제외한다.
7. 포함된 리뷰만 카테고리 분류와 추가 분석을 수행한다.
8. 집계 결과와 요약을 `apps/review-insights/data/analysis/`에 저장한다.
9. 프론트엔드는 `GET /api/games/{appid}/analysis`로 결과를 조회한다.

### 6.2 두 게임 비교 흐름

1. 사용자가 두 개의 게임을 선택한다.
2. 각 게임은 동일한 단일 게임 분석 파이프라인을 거친다.
3. 백엔드는 정규화된 분석 결과를 비교한다.
4. 프론트엔드는 비교 카드와 차트를 표시한다.

---

## 7. 데이터 모델 (Data Model)

저장 방식이 JSON 파일이더라도, 스키마는 명시적으로 유지한다.

### 7.1 원본 리뷰 레코드 (Raw Review Record)

```json
{
  "review_id": "123456789",
  "appid": 570,
  "review_text": "이 게임 재밌는데 버그가 많아요",
  "voted_up": false,
  "timestamp_created": 1712300000,
  "timestamp_updated": 1712300500,
  "playtime_forever": 1420,
  "playtime_at_review_hours": 21.5,
  "num_reviews": 8,
  "author_steamid": "7656119...",
  "received_at": "2026-04-09T15:30:00Z"
}
```

위 메타데이터는 Steam 응답에서 제공될 경우 정규화하여 저장한다.

- `playtime_forever`: 총 누적 플레이타임
- `playtime_at_review_hours`: 리뷰 작성 시점 플레이타임을 시간 단위로 정규화
- `num_reviews`: 작성자의 전체 리뷰 수

필드가 제공되지 않으면 `null`을 허용한다.

### 7.2 전처리된 리뷰 레코드 (Processed Review Record)

```json
{
  "review_id": "123456789",
  "appid": 570,
  "normalized_text": "이 게임 재밌는데 버그가 많아요",
  "hangul_ratio": 0.92,
  "is_korean": true,
  "is_low_quality": false,
  "is_profanity_only": false,
  "ambiguity_flags": [],
  "rule_decision": "include",
  "llm_invoked": false,
  "llm_decision": null,
  "llm_confidence": null,
  "final_decision_source": "rule",
  "included_in_analysis": true,
  "playtime_bucket": "experienced",
  "category_tags": ["bugs"],
  "primary_category": null,
  "canonical_theme": "버그 문제",
  "extracted_keywords": ["버그"],
  "time_bucket": "2026-W14"
}
```

### 7.3 분석 결과 레코드 (Analysis Result Record)

```json
{
  "appid": 570,
  "generated_at": "2026-04-09T15:35:00Z",
  "review_counts": {
    "raw_total": 500,
    "included_total": 310,
    "filtered_total": 190
  },
  "sentiment": {
    "positive": 180,
    "negative": 130,
    "positive_ratio": 0.58
  },
  "top_positive_themes": ["재미", "그래픽"],
  "top_negative_themes": ["버그", "최적화"],
  "category_distribution": {
    "bugs": 90,
    "performance": 70
  },
  "trend_points": [
    {
      "bucket": "2026-W13",
      "bugs": 12,
      "performance": 8
    }
  ],
  "playtime_segments": {
    "new_players": {
      "top_negative": ["온보딩"]
    },
    "experienced_players": {
      "top_negative": ["밸런스"]
    }
  },
  "issue_signals": {
    "bugs": {
      "mention_count": 90,
      "negative_ratio": 0.82,
      "recent_trend": "up",
      "experienced_player_share": 0.64,
      "themes": ["튕김", "충돌", "버그"],
      "sample_reviews": ["보스전에서 계속 튕김", "패치 이후 저장 오류가 생김"]
    },
    "performance": {
      "mention_count": 70,
      "negative_ratio": 0.88,
      "recent_trend": "flat",
      "experienced_player_share": 0.58,
      "themes": ["프레임드랍", "렉", "최적화"],
      "sample_reviews": ["마을에서 프레임이 반토막 남"]
    }
  },
  "sample_size_tier": "small",
  "trend_status": "limited",
  "trend_reason": "insufficient_recent_volume",
  "comparison_status": "compare_with_caution",
  "comparison_reason": "release_stage_mismatch",
  "warnings": [
    "이 결과는 수집된 한국어 리뷰 표본을 기준으로 합니다.",
    "분석 포함 리뷰 수가 적어 해석에 주의가 필요합니다."
  ],
  "summary": {
    "what_players_like": "...",
    "what_players_dislike": "...",
    "recent_change": "...",
    "fit_for": "...",
    "risks": "..."
  }
}
```

---

## 8. 저장 전략 (Storage Strategy)

MVP에서는 구조화된 로컬 파일을 사용한다.

### 8.1 디렉터리 구성

```text
apps/review-insights/data/
  raw/{appid}.json
  processed/{appid}.json
  analysis/{appid}.json
```

### 8.2 파일 기반 저장을 먼저 선택하는 이유

- 데이터베이스 설정 부담이 없다.
- 로컬에서 직접 확인하고 디버깅하기 쉽다.
- 1~2개 게임 분석에는 충분하다.
- 필요 시 나중에 교체하기 쉽다.

### 8.3 중요한 제약 사항

필터링된 리뷰도 플래그와 함께 전처리 결과에 반드시 남겨야 한다.

- 분석에서는 제외한다.
- 메타데이터는 반드시 보존한다.
- 규칙 기반 판정, LLM 판정, 최종 판정의 흔적을 함께 남긴다.

---

## 9. 리뷰 수집 설계 (Review Ingestion Design)

### 9.1 외부 데이터 소스

Steam Store 리뷰 엔드포인트:

```text
GET https://store.steampowered.com/appreviews/{appid}?json=1
```

### 9.2 최소 수집 파라미터

- `json=1`
- `language=all`
- `filter=recent`
- `review_type=all`
- `purchase_type=all`
- `num_per_page=100`
- `cursor=*`

### 9.3 MVP 수집 동작

- 제한된 수의 페이지만 가져온다.
- 선택된 각 게임에 대해 수동 실행 1회를 지원한다.
- 외부 필드를 내부 원본 스키마로 정규화한다.
- 전처리 전에 원본 응답을 즉시 저장한다.
- 주요 이슈 신호 해석에 필요한 작성자 메타데이터도 함께 정규화한다.

### 9.4 수집 구조 예시

```python
def fetch_reviews(appid: int, cursor: str = "*") -> dict:
    params = {
        "json": 1,
        "language": "all",
        "filter": "recent",
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": 100,
        "cursor": cursor,
    }
    response = requests.get(
        f"https://store.steampowered.com/appreviews/{appid}",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
```

이 코드는 설계 설명을 위한 예시이며 최종 구현 코드는 아니다.

### 9.5 주요 이슈 신호 해석용 메타데이터 정규화 원칙

주요 이슈 신호 해석에 사용할 핵심 메타데이터는 수집 단계에서 아래와 같이 정규화한다.

- `voted_up`
  - 리뷰 자체의 기본 방향성 신호
- `playtime_at_review_hours`
  - Steam 응답의 리뷰 작성 시점 플레이타임 필드가 존재하면 시간 단위로 정규화
  - 존재하지 않으면 `null`
- `num_reviews`
  - 작성자의 총 리뷰 수가 존재하면 저장
  - 존재하지 않으면 `null`

이 세 필드는 원본 리뷰 레코드와 전처리된 리뷰 레코드 모두에서 참조 가능하게 유지한다.

---

## 10. 전처리 설계 (Preprocessing Design)

전처리는 `결정론적 코어 + 선택적 LLM fallback` 구조를 따른다.
세부 규칙과 운영 기준은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 기준 문서로 삼는다.

이 계획서에서는 구현 관점의 핵심만 유지한다.

- 규칙 기반 정규화와 필터링이 기본 경로다.
- 애매한 리뷰 subset에만 LLM 보조 판정을 적용한다.
- 규칙 기반, LLM 기반, 최종 판정의 흔적을 저장한다.
- 원문은 항상 보존한다.

### 10.1 구현 대상

- 한글 비율 계산
- 저품질 / 욕설-only 판정
- 애매한 리뷰 선별
- LLM 호출 여부 결정
- 최종 포함/제외 결정 및 판정 메타데이터 저장

### 10.2 세부 정책 참조

아래 세부 항목은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 따른다.

- 한국어 판별 임계값
- 저품질 리뷰 기준
- 욕설-only 기준
- 구문 중심 정규화 규칙
- 애매한 리뷰 플래그
- LLM fallback 사용 범위
- 최종 판정 저장 필드

## 11. 카테고리 분류 설계 (Category Classification Design)

카테고리 분류는 규칙 기반 `multi-label`을 기본으로 한다.
세부 카테고리 체계와 멀티 라벨 집계 원칙은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 기준으로 유지한다.

### 11.1 구현 원칙

- 카테고리별 키워드/구문 사전을 유지한다.
- 하나의 리뷰에 여러 카테고리를 허용한다.
- `primary_category`는 필요 시 보조 필드로만 사용한다.
- 카테고리 집계는 `이슈 언급 수` 기준으로 해석한다.

### 11.2 초기 카테고리

- `bugs`
- `performance`
- `balance`
- `story`
- `graphics`
- `monetization`
- `multiplayer`
- `localization`
- `difficulty`
- `controls`

## 12. 키워드 / 테마 추출 설계 (Keyword / Theme Extraction Design)

키워드 / 테마 추출은 규칙 기반 집계를 기본으로 하고, 필요 시 canonical theme을 보조 신호로 활용한다.
세부 추출 우선순위와 해석 원칙은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 따른다.

### 12.1 구현 원칙

- 대표 구문과 phrase를 우선한다.
- 단일 unigram-only 접근에 고정하지 않는다.
- 긍정/부정 리뷰를 분리해 집계한다.
- 카테고리별 집계를 유지한다.

### 12.2 출력 예시

- 상위 긍정 키워드
- 상위 부정 키워드
- 카테고리별 상위 키워드
- 긍정 테마와 부정 테마

## 13. 트렌드 분석 설계 (Trend Analysis Design)

트렌드 분석은 “최근 무엇이 바뀌었는가?”에 답해야 한다.
다만 표본이 충분할 때만 강한 신호로 해석한다.

### 13.1 MVP 그룹화

- 리뷰를 주 단위로 그룹화한다.
- 주차별 카테고리 빈도를 계산한다.
- 최근 4주와 이전 4주를 비교한다.

### 13.2 트렌드 제한 원칙

어떤 카테고리가 상승 추세라고 판단되는 조건은 다음과 같다.

- 최근 카운트가 과거 카운트보다 의미 있게 높고
- 동시에 최근 카운트가 최소 기준치를 넘는 경우

- 최근 기간과 이전 기간 모두 최소 리뷰 수를 충족해야 한다.
- 비율 변화만으로 급증/급감을 판정하지 않는다.
- `최소 절대 증가량`과 `최소 리뷰 수`를 함께 충족해야 강한 추세 신호를 표시한다.
- 표본이 작은 경우 `trend_status`를 `limited` 또는 `unstable`로 표시한다.

초기 규칙 예시:

- `recent_count >= 5`
- `recent_count >= prior_count * 1.5`

세부 기준은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 따른다.

---

## 14. 주요 이슈 신호 설계 (Issue Signals Design)

MVP에서는 단일 우선순위 스코어를 계산하지 않는다.
대신 카테고리별 주요 이슈 신호를 집계해 사용자가 직접 판단할 수 있도록 한다.

### 14.1 구현 원칙

- `mention_count`
- `negative_ratio`
- `recent_trend`
- `experienced_player_share`
- `themes`
- `sample_reviews`
- `sample_size_tier`
- `warnings`

### 14.2 출력 원칙

- 주요 이슈 신호는 가능한 경우 모수와 함께 해석한다.
- 작은 표본에서는 경고 문구를 함께 제공한다.
- 주요 이슈 신호는 전체 유저 의견이 아니라 수집된 한국어 리뷰 표본 기반 신호로 간주한다.

세부 정의와 해석 방식은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 따른다.

---

## 15. 게임 비교 설계 (Comparison Design)

게임 비교는 항상 허용하지 않는다.

비교 전에는 다음 조건을 확인한다.

- 장르 유사성
- 가격 모델 유사성
- 출시 단계 유사성
- 리뷰 규모 차이
- 비교 기간 정렬 여부

출력 상태:

- `comparable`
- `compare_with_caution`
- `not_comparable`

비교가 제한되는 경우에는 결과를 숨기거나, 강한 경고 문구와 함께 제한적으로 표시한다.
세부 기준은 [analysis-policy.md](C:/Users/rubys/OneDrive/문서/IntelAI/NLP_PJ/docs/analysis-policy.md)를 따른다.

---

## 16. 플레이타임 세그먼트 설계 (Playtime Segmentation Design)

MVP 세그먼트는 두 개만 둔다.

- `new_players`: 플레이타임이 낮은 유저
- `experienced_players`: 플레이타임이 높은 유저

초기 기준:

- `< 120분` -> `new_players`
- `>= 120분` -> `experienced_players`

이 기준은 이후 조정 가능하지만 MVP에서는 충분하고 설명하기 쉽다.

### 15.1 두 개의 버킷만 사용하는 이유

- 설명이 쉽다.
- 초기 내부 인사이트 도출에 충분하다.
- 데이터가 적을 때 과도한 세분화를 피할 수 있다.

---

## 16. 요약 생성 설계 (Summary Generation Design)

요약 생성은 템플릿 기반으로 한다.

### 16.1 필수 요약 질문

- 플레이어들이 가장 좋아하는 것은 무엇인가?
- 플레이어들이 가장 많이 불평하는 것은 무엇인가?
- 최근에 무엇이 바뀌었는가?
- 이 게임은 누구에게 적합한가?
- 팀이 모니터링해야 하는 리스크는 무엇인가?

### 16.2 MVP 요약 방식

다음 요소로 요약 문장을 구성한다.

- 상위 긍정 테마
- 상위 부정 테마
- 최근 스파이크
- 플레이타임 세그먼트 차이

### 16.3 요약 조합 예시

```python
def build_summary(analysis: dict) -> dict:
    return {
        "what_players_like": f"플레이어들은 주로 {', '.join(analysis['top_positive_themes'][:2])}을 긍정적으로 언급합니다.",
        "what_players_dislike": f"가장 많이 언급된 불만은 {', '.join(analysis['top_negative_themes'][:2])}입니다.",
        "recent_change": analysis["recent_change_text"],
        "fit_for": analysis["fit_for_text"],
        "risks": analysis["risk_text"],
}
```

---

## 17. 백엔드 API 설계 (Backend API Design)

API는 작고 내부용으로 유지한다.

### 17.1 엔드포인트

#### `POST /api/ingest`

목적:

- 1개 또는 2개 게임을 수집하고 분석한다.

요청 예시:

```json
{
  "appids": [570]
}
```

응답 예시:

```json
{
  "status": "ok",
  "processed_appids": [570]
}
```

#### `GET /api/games/{appid}/analysis`

목적:

- 단일 게임의 분석 결과를 조회한다.

#### `GET /api/compare?appid1=570&appid2=730`

목적:

- 이미 분석된 두 게임을 비교한다.

#### `GET /api/games/{appid}/reviews`

목적:

- 디버깅과 검증을 위해 원본/전처리 리뷰 샘플을 확인한다.

#### `GET /api/health`

목적:

- 내부 상태 확인용 헬스 체크

### 17.2 API 예시

```python
@app.post("/api/ingest")
def ingest(payload: IngestRequest) -> dict:
    for appid in payload.appids:
        run_ingestion_and_analysis(appid)
    return {"status": "ok", "processed_appids": payload.appids}
```

---

## 18. 프론트엔드 대시보드 설계 (Frontend Dashboard Design)

대시보드는 화려할 필요 없이 기능적으로 동작하면 된다.

### 18.1 주요 화면

1. 단일 게임 분석 화면
2. 두 게임 비교 화면

### 18.2 UI 구성 요소

- 1개 또는 2개 appid 입력 필드
- 분석 실행 버튼
- 요약 카드
- 감성 비율 카드
- 표본 크기 라벨 또는 경고 배너
- 주요 이슈 신호 카드
- 카테고리 분포 차트
- 트렌드 차트
- 트렌드 제한 상태 표시
- 키워드/테마 목록
- 플레이타임 세그먼트 비교 패널
- 비교 가능 여부 표시
- 2개 게임 비교 테이블

### 18.3 UX 제약 사항

- 내부 도구 수준이면 충분하다.
- 완성도보다 명확성을 우선한다.
- 필터링된 리뷰 수와 포함된 리뷰 수를 명시적으로 보여준다.
- 제외된 리뷰 샘플을 쉽게 확인할 수 있어야 한다.
- 카테고리 집계는 `이슈 언급 수` 기준임을 명시한다.
- 단일 점수 기반 우선순위를 제시하지 않는다.
- 주요 이슈 신호는 해석용 근거이며, 최종 우선순위 판단은 사람이 수행한다는 점을 명시한다.
- 결과는 전체 유저 의견처럼 보이게 표현하지 않는다.
- 비율은 가능한 경우 모수와 함께 표시한다.
- 표본이 작은 경우 강한 요약 표현을 피하고 경고를 함께 표시한다.
- 비교가 부적절한 경우 비교 결과를 제한하거나 비활성화한다.

### 18.4 프론트엔드 예시

```javascript
async function runAnalysis(appids) {
  await fetch("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ appids }),
  });

  const results = await Promise.all(
    appids.map((appid) =>
      fetch(`/api/games/${appid}/analysis`).then((r) => r.json()),
    ),
  );

  renderDashboard(results);
}
```

---

## 19. 파일 단위 구현 계획 (File-by-File Implementation Plan)

이 섹션은 실제 코드 구현 전에 무엇을 변경할지 설명한다.

### Phase 1: 프로젝트 골격

생성:

- `backend/app.py`
- `backend/models/schemas.py`
- `backend/api/routes.py`
- `data/raw/.gitkeep`
- `data/processed/.gitkeep`
- `data/analysis/.gitkeep`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/backend/app.py`
- `apps/review-insights/backend/models/schemas.py`
- `apps/review-insights/backend/api/routes.py`
- `apps/review-insights/data/raw/.gitkeep`
- `apps/review-insights/data/processed/.gitkeep`
- `apps/review-insights/data/analysis/.gitkeep`

목적:

- 실행 가능한 최소 API 구조 수립

### Phase 2: 저장소와 수집

생성:

- `backend/storage/file_store.py`
- `backend/services/steam_reviews.py`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/backend/storage/file_store.py`
- `apps/review-insights/backend/services/steam_reviews.py`

목적:

- 리뷰 수집
- 원본 payload 저장
- 내부 원본 리뷰 레코드 형식으로 정규화

### Phase 3: 전처리 규칙

생성:

- `backend/analysis/preprocess.py`
- `backend/analysis/rules.py`
- `backend/analysis/llm_preprocess.py`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/backend/analysis/preprocess.py`
- `apps/review-insights/backend/analysis/rules.py`

목적:

- 텍스트 정규화
- 한글 비율 계산
- 저품질 필터링
- 욕설-only 필터링
- 애매한 리뷰 선별
- LLM 호출 여부 결정

### Phase 4: 분석 로직

생성:

- `backend/analysis/categorize.py`
- `backend/analysis/themes.py`
- `backend/analysis/trends.py`
- `backend/analysis/summarize.py`
- `backend/services/analysis_service.py`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/backend/analysis/categorize.py`
- `apps/review-insights/backend/analysis/themes.py`
- `apps/review-insights/backend/analysis/trends.py`
- `apps/review-insights/backend/analysis/summarize.py`
- `apps/review-insights/backend/services/analysis_service.py`

목적:

- 멀티 라벨 카테고리 태깅
- phrase/canonical theme 기반 키워드 집계
- 트렌드 감지
- 주요 이슈 신호 집계
- 요약 결과 조합

### Phase 5: API 완성

수정:

- `backend/api/routes.py`
- `backend/app.py`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/backend/api/routes.py`
- `apps/review-insights/backend/app.py`

목적:

- ingest, analysis, compare, reviews, health 엔드포인트 노출

### Phase 6: 대시보드

생성:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/frontend/index.html`
- `apps/review-insights/frontend/app.js`
- `apps/review-insights/frontend/styles.css`

목적:

- 1~2개 게임 분석용 최소 내부 대시보드 구축

### Phase 7: 테스트

생성:

- `tests/test_preprocess.py`
- `tests/test_categorize.py`
- `tests/test_trends.py`

앱 분리 구조 적용 후 경로:

- `apps/review-insights/tests/test_preprocess.py`
- `apps/review-insights/tests/test_categorize.py`
- `apps/review-insights/tests/test_trends.py`

목적:

- 핵심 결정론적 규칙 검증

### Phase 8: 문서화

생성/수정:

- `README.md`
- `docs/architecture.md`
- `docs/analysis-policy.md`
- `docs/review-insights-app-structure.md`
- `apps/review-insights/docs/runbook.md`
- `apps/review-insights/docs/api.md`
- 필요 시 `steam-review-insights-spec.md`

목적:

- 실행, 테스트, 검증 방법 설명

---

## 20. 테스트 계획 (Testing Plan)

로직이 결정론적이므로 테스트는 핵심 판단에 집중한다.

### 20.1 반드시 테스트할 로직

- 한글 비율 분류
- 저품질 필터링
- 욕설-only 필터링
- 카테고리 매핑
- 멀티 라벨 카테고리 매핑
- 트렌드 스파이크 감지
- 플레이타임 버킷 할당
- 애매한 리뷰 선별 규칙
- LLM 호출 여부 결정 규칙
- 주요 이슈 신호 집계
- 메타데이터 누락 시 fallback 처리

### 20.2 예시 테스트 케이스

- 실행 가능한 불만이 있는 한국어 리뷰는 포함된다.
- 영어-only 리뷰는 제외된다.
- 욕설-only 리뷰는 제외된다.
- 욕설 + 카테고리 단서가 있는 리뷰는 포함된다.
- `최적화`를 언급하면 `performance`로 태깅된다.
- 하나의 리뷰가 `performance`와 `multiplayer`에 동시에 태깅될 수 있다.
- 최근 카테고리 급증은 스파이크로 감지된다.
- 숙련 유저 비중과 부정 비율이 카테고리별 신호에 반영된다.

### 20.3 전처리 테스트 예시

세부 테스트 케이스와 정책 기반 판정 기준은 `docs/analysis-policy.md`를 기준으로 정리하고,
구현 시 실제 테스트 파일에서 구체화한다.

---

## 21. 아키텍처 결정 사항 (Architecture Decisions)

### 결정 1: ML이 아니라 결정론적 분석 사용

이유:

- 명세와 AGENTS 규칙에서 명시적으로 요구한다.
- 검증이 쉽다.
- MVP에 적합하다.

### 결정 2: 제품별 앱 디렉터리로 먼저 분리

이유:

- 현재 서비스와 팀원의 서비스 목적이 다르다.
- 파일 구조, API, 테스트, 데이터 경로 충돌을 줄일 수 있다.
- 공통화보다 제품 경계 보호가 우선이다.

### 결정 3: DB가 아니라 파일 기반 저장 사용

이유:

- 현재 규모가 매우 작다.
- 설정 및 유지 비용이 낮다.
- 디버깅이 단순하다.

### 결정 4: 전처리는 결정론적 코어 + LLM fallback 사용

이유:

- 기본 전처리는 설명 가능하고 재현성이 높아야 한다.
- LLM은 반어, 비유, 욕설 포함 유의미 불만 같은 애매한 케이스 보완에 유리하다.
- 전체 리뷰가 아닌 일부 subset에만 적용하면 비용과 복잡도를 통제할 수 있다.
- LLM은 선택적 보조 계층이며, 응답 필드가 없거나 비용 제약이 있더라도 시스템이 동작해야 한다.

### 결정 5: 규칙 기반 멀티 라벨 카테고리 매핑 사용

이유:

- 설명 가능하다.
- 점진적 개선이 쉽다.
- 내부 MVP 반복 개발에 안정적이다.
- 리뷰 1건이 여러 문제를 동시에 담을 수 있는 실제 데이터를 더 잘 반영한다.

### 결정 6: 단일 우선순위 스코어는 MVP에서 사용하지 않음

이유:

- 현재 단계에서 객관적 중요도를 하나의 수치로 정당화하기 어렵다.
- NLP 오차를 하나의 숫자로 압축하면 과신 위험이 커진다.
- 내부 팀이 직접 판단할 수 있는 설명 가능한 신호 제공이 MVP에 더 적합하다.

### 결정 7: 템플릿 기반 요약 생성 사용

이유:

- 숨겨진 모델 동작을 피할 수 있다.
- 출력이 예측 가능하다.
- 초기 이해관계자 사용에 충분하다.

### 결정 8: 프론트엔드는 단순하고 얇게 유지

이유:

- 핵심 가치는 분석에 있다.
- 내부 사용자는 화려함보다 명확성을 더 원한다.

---

## 22. 가정 (Assumptions)

- MVP에서는 Steam 공개 리뷰 엔드포인트를 사용해 리뷰 수집이 가능하다.
- 첫 버전은 수동 분석 실행만 지원하면 된다.
- 한글 비율 필터링, 구문 기반 정규화, 카테고리 규칙만으로 1차 품질을 확보할 수 있다.
- 애매한 일부 리뷰는 LLM 보조 판정이 필요할 수 있다.
- `playtime_at_review_hours`와 `num_reviews`는 외부 응답에 없을 수 있으므로 `null` 허용 설계를 전제로 한다.
- 사용자는 appid를 직접 입력하거나, 이후 아주 작은 사전 정의 목록에서 선택할 수 있다.
- MVP 수준의 리뷰 수는 동기 처리로 충분히 감당 가능하다.
- 다른 팀 서비스와 공통 모듈은 아직 추출하지 않는 것이 더 안전하다.

---

## 23. 리스크와 완화 방안 (Risks and Mitigations)

### 리스크: 한글 비율 기준이 혼합 언어지만 유용한 리뷰를 제외할 수 있다

완화 방안:

- threshold를 명시적으로 유지하고 조정 가능하게 만든다.
- 필터링된 리뷰 메타데이터를 보존해 검토 가능하게 한다.

### 리스크: 규칙 기반 카테고리가 동의어를 놓칠 수 있다

완화 방안:

- 키워드 사전을 중앙에서 관리하고 쉽게 확장 가능하게 만든다.
- 대표 구문과 canonical theme 기반 보조 신호를 사용한다.

### 리스크: LLM 보조 판정이 재현성과 비용 문제를 만들 수 있다

완화 방안:

- 애매한 리뷰 subset에만 호출한다.
- 구조화된 JSON 출력만 수용한다.
- 프롬프트 버전과 confidence를 저장한다.
- 규칙 기반 결과와 LLM 결과를 함께 보존한다.

### 리스크: 파일 기반 저장이 한계가 될 수 있다

완화 방안:

- 저장 로직을 `file_store.py` 뒤에 격리한다.

### 리스크: 요약 문장이 반복적으로 느껴질 수 있다

완화 방안:

- MVP에서는 수용한다.
- 지금 LLM 복잡성을 넣지 않고 이후 템플릿 개선으로 대응한다.

---

## 24. 권장 구현 순서 (Recommended Build Order)

구현은 작고 리뷰 가능한 단위로 아래 순서를 따른다.

1. 백엔드 골격 + 스키마
2. 저장소 + 수집
3. 전처리 규칙 + 애매한 리뷰 선별
4. 멀티 라벨 카테고리 및 테마 추출
5. 주요 이슈 신호
6. 트렌드 분석
7. 요약 생성기
8. API 통합
9. 대시보드
10. 테스트
11. 문서 업데이트

---

## 25. MVP 완료 기준 (Definition of Done for MVP)

다음 조건이 충족되면 MVP가 완료된 것으로 본다.

- 하나의 게임을 end-to-end로 수집하고 분석할 수 있다.
- 두 개의 게임을 조건부로 비교할 수 있다.
- 한국어가 아닌 리뷰 / 저품질 리뷰 / 욕설-only 리뷰가 분석에서 제외된다.
- 애매한 리뷰에 대한 LLM 보조 판정 정책이 정의되고 저장된다.
- 필터링된 리뷰도 메타데이터를 유지한다.
- 규칙 기반, LLM 기반, 최종 판정의 흔적이 저장된다.
- 카테고리와 키워드가 대시보드에 표시된다.
- 카테고리는 멀티 라벨 기준으로 집계된다.
- 주요 이슈 신호와 대표 리뷰가 대시보드에 표시된다.
- 트렌드가 단순한 차트로 표시된다.
- 비교 가능 여부와 해석 주의 상태가 결과에 반영된다.
- 표본 크기와 트렌드 제한 상태가 결과에 반영된다.
- 요약이 제품에서 요구한 다섯 가지 질문에 답한다.
- 최소 테스트가 핵심 결정론적 규칙을 커버한다.
- 로컬 실행 및 테스트 방법이 문서에 정리되어 있다.

---

## 26. 다음 단계 (Next Step)

다음 구현 단계는 아래 순서로 진행한다.

- 먼저 백엔드 골격만 생성한다.
- 그 다음 나머지 분석 스택을 만들기 전에 전처리 규칙을 추가한다.

이 순서는 첫 번째 코드 마일스톤을 작고, 테스트 가능하며, MVP 범위에 맞게 유지해준다.
