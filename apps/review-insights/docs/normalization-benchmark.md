# 정규화 벤치마크 운영 문서

## 1. 목적

이 문서는 Steam 한국어 리뷰 정규화 품질을 반복적으로 점검하기 위한 벤치마크 운영 기준을 정의한다.

이 벤치마크의 목적은 다음과 같다.

- 규칙 기반 전처리와 카테고리 분류가 어떤 유형의 리뷰를 놓치는지 확인한다.
- 장르별로 반복되는 미분류 표현과 테마 누락 패턴을 식별한다.
- 정규화 사전, 카테고리 규칙, 테마 패턴을 보강한 뒤 동일 코호트로 재측정한다.
- 개선 전후 지표를 비교해 실제 품질 향상 여부를 확인한다.

이 문서는 품질 진단용 기준 문서이며, 제품 사용자용 리포트 기준 문서는 아니다.

---

## 2. 운영 원칙

- 동일한 게임 코호트를 반복 사용한다.
- 수집 조건은 가능한 한 동일하게 유지한다.
- 정규화 규칙은 자동 반영하지 않는다.
- 자동화는 문제 탐지와 요약까지만 담당한다.
- 규칙 수정, 카테고리 확장, 사전 보강은 사람이 검토 후 결정한다.
- 이 벤치마크는 제품 KPI가 아니라 내부 품질 개선 도구이다.

---

## 3. 대표 버킷 정의

정규화 실패 패턴을 확인하기 위해 Steam 장르를 아래 상위 버킷으로 묶는다.

- 액션 / 슈터
- RPG / 스토리 중심
- 시뮬레이션 / 라이프심
- 생존 / 제작 / 샌드박스
- 전략 / 전술 / 카드
- 로그라이크 / 로그라이트
- 호러 / 긴장감 중심
- 스포츠 / 레이싱

보조 태그는 다음과 같이 사용한다.

- 멀티플레이
- 라이브서비스
- 얼리액세스
- 정식 출시

대표 버킷은 게임당 1개만 부여한다.
보조 태그는 0개 이상 부여할 수 있다.

---

## 4. 기준 코호트

이 벤치마크는 Steam Deck 기준 대표 게임 코호트를 사용한다.

| appid | 게임명 | 대표 버킷 | 보조 태그 | 기대 정규화 실패 패턴 |
|---|---|---|---|---|
| 1091500 | 사이버펑크 2077 | RPG / 스토리 중심 | 정식 출시 | 감성형 praise와 성능/버그 불만이 한 리뷰 안에 섞이는 경우 |
| 1174180 | 레드 데드 리뎀션 2 | RPG / 스토리 중심 | 정식 출시 | 장문 몰입형 감상에서 실제 이슈와 분위기 praise를 분리하기 어려운 경우 |
| 1222670 | 더 심즈 4 | 시뮬레이션 / 라이프심 | 정식 출시 | 커스터마이징, 건축, 생활 콘텐츠 표현이 여러 주제로 동시에 겹치는 경우 |
| 252490 | 러스트 | 생존 / 제작 / 샌드박스 | 멀티플레이 | 생존 스트레스, 제작, 레이드, 갈등 표현이 짧고 거칠게 섞이는 경우 |
| 230410 | 워프레임 | 액션 / 슈터 | 라이브서비스 | 파밍 praise와 반복 피로감, 운영/업데이트 평가가 함께 나오는 경우 |
| 1145350 | 하데스 II | 로그라이크 / 로그라이트 | 얼리액세스 | 빌드, 반복성, 중독성 praise를 단순 긍정 감상과 구분하기 어려운 경우 |
| 381210 | 데드 바이 데이라이트 | 호러 / 긴장감 중심 | 멀티플레이 + 라이브서비스 | 짧고 감정적인 리뷰에서 실제 밸런스/매칭 불만을 추출하기 어려운 경우 |
| 275850 | 노 맨즈 스카이 | 생존 / 제작 / 샌드박스 | 정식 출시 | 탐험 감상, 콘텐츠 볼륨, 최적화, 반복 플레이 표현이 넓게 섞이는 경우 |

---

## 5. 배치 실행 순서

배치 분석은 아래 순서로 수행한다.

### 5.1 ingest

목적:
- 각 게임의 raw 리뷰를 동일 조건으로 수집한다.

기본 조건:
- `review_pages = all`
- `language = koreana`
- `filter = recent`
- 내부 수집 cap = 200 pages

확인 항목:
- 수집 성공 여부
- `fetched_pages`
- `fetched_review_count`
- `all_mode_cap_reached`
- metadata 존재 여부

### 5.2 processed 점검

목적:
- 전처리와 규칙 기반 분류가 정상 작동했는지 확인한다.

확인 항목:
- `included_in_analysis` 비율
- `exclude_low_quality` 비율
- `exclude_non_korean` 비율
- `exclude_profanity_only` 비율
- `category_tags` 누락 비율
- `canonical_theme` 누락 비율
- `ambiguity_flags` 발생 비율

### 5.3 지표 집계

목적:
- 게임별 품질 상태를 동일 형식으로 비교 가능하게 만든다.

출력 항목:
- raw 리뷰 수
- 포함 리뷰 수
- 포함 비율
- 저품질 제외 수
- 비한국어 제외 수
- 욕설-only 제외 수
- `unclassified_included` 수 / 비율
- `canonical_theme_missing` 수 / 비율
- `ambiguity_flag` 리뷰 수 / 비율
- `fetched_pages`
- `all_mode_cap_reached`

### 5.4 실패 패턴 정리

목적:
- 어떤 규칙이 어떤 버킷에서 반복적으로 실패하는지 정리한다.

### 5.5 규칙 수정 후 재실행

목적:
- 동일 코호트 기준으로 개선 전후 차이를 비교한다.

---

## 6. 품질 지표 정의

### 6.1 핵심 지표

- raw 리뷰 수
- 포함 리뷰 수
- 포함 비율
- `unclassified_included` 수
- `unclassified_included` 비율
- `canonical_theme_missing` 수
- `canonical_theme_missing` 비율
- `ambiguity_flag` 리뷰 수
- `ambiguity_flag` 비율

### 6.2 보조 지표

- 저품질 제외 수
- 비한국어 제외 수
- 욕설-only 제외 수
- `fetched_pages`
- `all_mode_cap_reached`

### 6.3 데이터 소스 분리

#### processed.json 기반 계산 필드

아래 필드는 `processed/{appid}.json`을 기준으로 계산한다.

- `included_review_count`
- `excluded_low_quality_count`
- `excluded_non_korean_count`
- `excluded_profanity_only_count`
- `unclassified_included_count`
- `canonical_theme_missing_count`
- `ambiguity_flagged_count`
- `category_counter`
- `ambiguity_flag_counter`
- `included_ratio`
- `unclassified_included_ratio`
- `canonical_theme_missing_ratio`
- `ambiguity_flagged_ratio`
- `top_unclassified_samples`
- `top_theme_missing_samples`
- `top_ambiguity_samples`
- `top_non_korean_samples`
- `top_low_quality_samples`

#### analysis.json 기반 참조 필드

아래 필드는 `analysis/{appid}.json`에서 읽어 수집 메타데이터로 사용한다.

- `fetched_pages`
- `fetched_review_count`
- `fetch_timeout_seconds`
- `fetch_filter`
- `all_mode_page_cap`
- `all_mode_cap_reached`
- `review_pages`

#### metadata.json 기반 보조 필드

아래 필드는 `metadata/{appid}.json`에서 읽어 리포트 문맥 보강에 사용한다.

- `game_name`
- `genres`
- `price_model`
- `release_stage`

raw 총량은 `raw/{appid}.json` 길이를 기준으로 계산하는 것을 기본으로 한다.

### 6.4 해석 우선순위

가장 우선적으로 보는 지표는 다음과 같다.

- `unclassified_included` 비율
- `canonical_theme_missing` 비율
- `ambiguity_flag` 비율

이 세 지표는 각각 다음을 의미한다.

- `unclassified_included` 비율이 높다:
  카테고리 규칙 또는 정규화 사전이 실제 표현을 충분히 포착하지 못함
- `canonical_theme_missing` 비율이 높다:
  카테고리는 맞았지만 대표 테마 패턴이 부족함
- `ambiguity_flag` 비율이 높다:
  규칙 경계가 넓거나, LLM fallback 대상 정의가 부족함

---

## 7. 샘플 리뷰 추출 규칙

### 7.1 미분류 포함 리뷰 샘플

조건:
- `included_in_analysis = true`
- `category_tags = []`

목적:
- 정규화 사전 보강과 카테고리 확장 후보 확인

권장 개수:
- 게임당 최대 20개

### 7.2 테마 누락 리뷰 샘플

조건:
- `included_in_analysis = true`
- `category_tags != []`
- `canonical_theme = null`

목적:
- theme pattern 보강 후보 확인

권장 개수:
- 게임당 최대 15개

### 7.3 ambiguity_flags 리뷰 샘플

조건:
- `ambiguity_flags` 길이 >= 1

목적:
- 규칙 경계와 향후 LLM fallback 후보 확인

권장 개수:
- 게임당 최대 20개

### 7.4 비한국어 제외 리뷰 샘플

조건:
- `rule_decision = exclude_non_korean`

목적:
- 한국어 비율 규칙 점검

권장 개수:
- 게임당 최대 10개

### 7.5 저품질 제외 리뷰 샘플

조건:
- `rule_decision = exclude_low_quality`

목적:
- 저품질 규칙 과잉/과소 제외 여부 점검

권장 개수:
- 게임당 최대 10개

---

## 8. notes 생성 규칙

아래 조건에 따라 요약 메모를 생성한다.

- `all_mode_cap_reached = true`
  - 부분 수집 상태이므로 해석에 주의 필요
- `unclassified_included_ratio >= 0.30`
  - 카테고리 확장 또는 정규화 사전 보강 필요
- `unclassified_included_ratio >= 0.50`
  - 현재 taxonomy가 게임 표현을 충분히 포착하지 못함
- `canonical_theme_missing_ratio >= 0.15`
  - theme pattern 보강 필요
- `canonical_theme_missing_ratio >= 0.30`
  - 대표 테마 해석 신뢰도가 낮음
- `ambiguity_flagged_ratio >= 0.20`
  - 규칙 경계 점검 필요
- `ambiguity_flagged_ratio >= 0.40`
  - ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요
- `excluded_non_korean_count / raw_review_count >= 0.10`
  - 한국어 필터 점검 필요
- `excluded_low_quality_count / raw_review_count >= 0.15`
  - 저품질 규칙 또는 장르 특성 점검 필요
- `included_review_count < 200`
  - 표본 수가 작아 해석에 주의 필요

---

## 9. 산출물 형식

권장 산출물은 다음과 같다.

- Markdown 리포트 1개
- JSON 요약 파일 1개

권장 파일명은 다음과 같다.

- `batch_quality_report.md`
- `batch_quality_report.json`

---

## 10. 테스트 기준

최소 테스트는 아래 범위를 포함한다.

- 집계 함수 테스트
- 비율 계산 테스트
- 샘플 리뷰 추출 테스트
- notes 생성 테스트
- 최종 summary record 조립 테스트
- batch report 이상치 분류 테스트

---

## 11. 제외 범위

이 벤치마크는 다음 범위를 포함하지 않는다.

- Steam 리뷰 재수집 자동화
- 규칙 자동 수정
- 카테고리 자동 생성
- LLM 자동 호출
- 제품 UI 자동 변경
- 우선순위 점수 계산

---

## 12. cohort-file 사용 예시

기본 코호트 대신 실험용 코호트를 사용하고 싶다면 JSON 파일을 만들어 `--cohort-file` 옵션으로 주입한다.

지원 형식은 다음 둘 중 하나다.

```json
[
  {
    "appid": 2456740,
    "game_name": "inZOI",
    "primary_bucket": "시뮬레이션 / 라이프심",
    "secondary_tags": ["얼리액세스"],
    "expected_failure_pattern": "건축, 커스터마이징, 콘텐츠 부족 표현이 겹치는 경우"
  }
]
```

```json
{
  "cohort": [
    {
      "appid": 1049590,
      "game_name": "이터널 리턴",
      "primary_bucket": "액션 / 슈터",
      "secondary_tags": ["라이브서비스"],
      "expected_failure_pattern": "짧은 밸런스, 매칭, 운영 불만 표현이 반복되는 경우"
    }
  ]
}
```

실행 예시:

```bash
python apps/review-insights/scripts/batch_quality_report.py --cohort-file apps/review-insights/data/reports/experimental_cohort.json
```

특정 appid만 다시 제한하고 싶다면 `--appids`를 함께 사용할 수 있다.

```bash
python apps/review-insights/scripts/batch_quality_report.py --cohort-file apps/review-insights/data/reports/experimental_cohort.json --appids 2456740
```
