# review-insights Runbook

## 1. 목적

이 문서는 `apps/review-insights/` 앱의 현재 로컬 실행 방법, API 사용 방법, 저장 파일 위치, 디버깅 흐름을 정리한다.

현재 구현 범위:

- Steam 리뷰 다중 페이지 fetch(기본 all) 또는 수동 `steam_payload` 주입
- Steam appdetails 기반 게임 메타데이터 수집
- 결정론적 전처리
- 멀티 라벨 카테고리 분류
- canonical theme 추출
- 트렌드 상태 계산
- 요약 생성
- raw / metadata / processed / analysis 파일 저장
- 게임 비교 API
- 비교 UI가 포함된 간단한 내부 대시보드

---

## 2. 현재 엔드포인트

- `GET /`
- `GET /api/health`
- `POST /api/ingest`
- `GET /api/games/{appid}/metadata`
- `GET /api/games/{appid}/raw`
- `GET /api/games/{appid}/processed`
- `GET /api/games/{appid}/analysis`
- `GET /api/compare?appid1=...&appid2=...`

`GET /`는 내부 대시보드 페이지를 반환한다.

---

## 3. 실행 준비

현재 백엔드는 FastAPI와 Uvicorn 기준으로 동작한다.

필수 전제:

- Python 실행 가능
- `fastapi`
- `uvicorn`

현재 디렉터리 이름에 하이픈(`review-insights`)이 포함되어 있으므로, 일반적인 패키지 import 경로 대신 `--app-dir` 방식으로 서버를 실행한다.

---

## 4. 로컬 실행

프로젝트 루트에서 아래 명령으로 서버를 실행한다.

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

기본 접속 경로:

- 대시보드: `http://127.0.0.1:8000/`
- 헬스체크: `http://127.0.0.1:8000/api/health`

수동 점검 시 검증했던 명령 예시:

```bash
uvicorn app:app --app-dir apps/review-insights/backend --host 127.0.0.1 --port 8765
```

---

## 5. 대시보드 사용 방법

### 5.1 단일 분석

1. 서버를 실행한다.
2. 브라우저에서 `/` 경로를 연다.
3. `단일 분석 appid`에 Steam appid를 입력한다.
4. `review pages`(all / 1p / 4p / 10p)를 선택한다.
5. `분석 실행` 버튼을 누른다.
6. 아래 결과를 확인한다.

표시 항목:

- 표본 등급
- 트렌드 상태
- 경고 문구
- 요약 결과
- 주요 이슈 신호 카드
- analysis JSON
- raw 디버그 뷰
- processed 디버그 뷰

`processed` 패널에서는 `filter`에서 `all / included_only / excluded_only`를 선택해 분석 포함/제외 리뷰를 빠르게 나눠 볼 수 있다.

### 5.2 두 게임 비교

1. `비교할 appid 2개` 입력 영역에 두 appid를 넣는다.
2. `비교 실행` 버튼을 누른다.
3. 앱은 두 게임을 먼저 개별 분석한 뒤 비교 API를 호출한다.
4. 비교 상태, 경고, 공통 이슈, 각 게임에만 있는 이슈를 확인한다.

표시 항목:

- `comparison_status`
- `comparison_reason`
- 비교 요약
- 게임별 표본 등급 / 트렌드 상태 / 이슈 수
- 게임별 메타데이터
- 공통 이슈 카테고리
- 각 게임에만 있는 이슈 카테고리
- 비교 경고 문구
- comparison JSON

주의:

- 현재 비교 결과는 우열 판단이 아니라 `리뷰 패턴 차이 확인용`이다.
- 장르, 가격 모델, 출시 단계 메타데이터를 활용하지만 여전히 보수적으로 판정한다.

---

## 6. API 사용 방법

### 6.1 `POST /api/ingest`

세 가지 입력 방식이 가능하다.

#### 방식 A: `appid`만 전달

백엔드가 Steam Store 리뷰 API와 appdetails API에서 직접 데이터를 가져온다.
리뷰 수집 언어 기본값은 `koreana`, 페이지 수 기본값은 `all`이다.

예시:

```json
{
  "appid": 570
}
```

#### 방식 B: `steam_payload` 직접 전달

테스트나 로컬 확인용으로 Steam 리뷰 응답 형태의 payload를 직접 넣을 수 있다.

예시:

```json
{
  "appid": 570,
  "steam_payload": {
    "reviews": [
      {
        "recommendationid": "1001",
        "review": "최적화가 별로라 프레임 드랍이 심함",
        "voted_up": false,
        "timestamp_created": 1704067200,
        "timestamp_updated": 1704067200,
        "author": {
          "steamid": "steamid-1001",
          "playtime_forever": 180,
          "playtime_at_review": 120,
          "num_reviews": 4
        }
      }
    ]
  }
}
```

#### 방식 C: `game_metadata_payload` 직접 전달

비교 판정 품질을 테스트하려면 appdetails 형태의 메타데이터 payload도 함께 넣을 수 있다.

#### 방식 D: `review_pages`로 수집 페이지 수 조절

기본값은 `all`이며, `all` 모드는 내부적으로 최대 `200페이지`까지만 수집한다.  
필요 시 `1`부터 `10`까지 지정할 수 있다.

예시:

```json
{
  "appid": 1551360,
  "review_pages": "all"
}
```

응답 예시:

```json
{
  "appid": 570,
  "raw_review_count": 1,
  "processed_review_count": 1,
  "included_review_count": 1,
  "sample_size_tier": "very_small",
  "trend_status": "limited",
  "review_pages": "all",
  "fetched_pages": 3,
  "fetched_review_count": 217,
  "fetch_timeout_seconds": 20,
  "fetch_filter": "recent",
  "all_mode_page_cap": 200,
  "all_mode_cap_reached": false,
  "metadata_collected": true,
  "price_model": "paid",
  "release_stage": "released"
}
```

`review_pages="all"` 실행 시 응답에는 수집 진행 확인용 메타데이터(`fetched_pages`, `fetched_review_count`, `fetch_timeout_seconds`, `fetch_filter`, `all_mode_page_cap`, `all_mode_cap_reached`)가 포함된다.
같은 ingest로 저장된 `GET /api/games/{appid}/analysis` 결과에도 `all_mode_page_cap`, `all_mode_cap_reached`가 함께 포함된다.

### 6.2 `GET /api/games/{appid}/metadata`

저장된 게임 메타데이터를 반환한다.

예시:

```text
GET /api/games/570/metadata
```

### 6.3 `GET /api/games/{appid}/raw`

정규화된 raw 리뷰 레코드를 반환한다.

예시:

```text
GET /api/games/570/raw
```

### 6.4 `GET /api/games/{appid}/processed`

전처리와 카테고리 분류를 거친 processed 리뷰 레코드를 반환한다.

예시:

```text
GET /api/games/570/processed
```

### 6.5 `GET /api/games/{appid}/analysis`

최종 분석 결과 JSON을 반환한다.

예시:

```text
GET /api/games/570/analysis
```

### 6.6 `GET /api/compare?appid1=...&appid2=...`

두 게임의 저장된 분석 결과와 메타데이터를 비교한다.

예시:

```text
GET /api/compare?appid1=570&appid2=730
```

현재 비교 결과에는 다음 정보가 포함된다.

- `comparison_status`
- `comparison_reason`
- `warnings`
- 공통 이슈 카테고리
- 각 게임에만 있는 이슈 카테고리
- 비교 요약
- 게임별 메타데이터

현재 비교 정책은 보수적이다.

- 표본이 너무 작으면 `not_comparable`
- 리뷰 규모 차이가 크면 `compare_with_caution`
- 출시 단계가 크게 다르면 `not_comparable`
- 장르 또는 가격 모델 차이가 있으면 `compare_with_caution`

즉, 비교 결과는 우열 판정보다 `리뷰 패턴 차이 확인용`으로 해석해야 한다.

---

## 7. 저장 파일 위치

분석을 실행하면 아래 경로에 파일이 저장된다.

```text
apps/review-insights/data/
  metadata/{appid}.json
  raw/{appid}.json
  processed/{appid}.json
  analysis/{appid}.json
```

각 파일 의미:

- `metadata`
  - 비교 판정 보조에 사용하는 장르 / 가격 모델 / 출시 단계 정보
- `raw`
  - Steam 응답을 내부 `RawReview` 스키마로 정규화한 결과
- `processed`
  - 전처리, 포함/제외, 카테고리, canonical theme 반영 결과
- `analysis`
  - 주요 이슈 신호, 표본 등급, 경고, 트렌드 상태, 요약이 포함된 최종 결과

---

## 8. 테스트 실행

현재 테스트는 표준 `unittest` 기준이다.

전체 테스트 예시:

```bash
python -m unittest apps/review-insights/tests/test_preprocess.py apps/review-insights/tests/test_categorize.py apps/review-insights/tests/test_themes.py apps/review-insights/tests/test_trends.py apps/review-insights/tests/test_summarize.py apps/review-insights/tests/test_analysis_service.py apps/review-insights/tests/test_ingestion_and_storage.py apps/review-insights/tests/test_api_flow.py apps/review-insights/tests/test_compare_service.py
```

현재 검증되는 항목:

- 한글 비율 판정
- 저품질 필터링
- 욕설-only 필터링
- 카테고리 분류
- canonical theme 추출
- 트렌드 상태 계산
- 요약 생성
- 분석 결과 조립
- 파일 저장
- API helper 흐름
- 메타데이터 정규화
- 비교 API 조립

---

## 9. 수동 점검 메모

로컬 서버 기준으로 아래 흐름은 실제로 수동 점검했다.

- `GET /`
- `GET /api/health`
- `POST /api/ingest`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/raw`
- `GET /api/games/{appid}/processed`

점검 예시에서는 다음 값이 정상 반환됐다.

- `raw_review_count=2`
- `processed_review_count=2`
- `included_review_count=2`
- `sample_size_tier=very_small`
- `trend_status=limited`

비교 API는 자동 테스트로 검증했고, 현재 대시보드에서도 직접 호출할 수 있다.

---

## 10. 현재 한계

- Steam fetch 기본값은 `all`이며, `all` 모드 최대 수집량은 `200페이지`로 제한된다. 필요 시 `1~10` 페이지를 명시할 수 있다.
- 비교 상태는 메타데이터가 있어도 여전히 보수적으로 판정한다.
- 대시보드는 내부 확인용 최소 화면이다.

---

## 11. 디버깅 팁

- 결과가 이상하면 먼저 `raw`를 확인한다.
- 전처리와 카테고리 태깅이 의심되면 `processed`를 확인한다.
- 비교 상태가 의심되면 `metadata`를 확인한다.
- 최종 경고, 표본 등급, 요약은 `analysis`를 확인한다.
- 브라우저에서는 대시보드 하단의 raw / processed 디버그 뷰와 비교 패널을 우선 사용한다.

---

## 12. 다음 후보 작업

- 비교 판정에 필요한 게임 메타데이터 범위 확장
- 디버그 JSON 패널 접기/펼치기 UI 추가
- 비교 결과를 더 읽기 쉽게 카드와 표 형태로 다듬기

---

## 13. ����ȭ ��ġ��ũ ����Ʈ

����ȭ ��ġ��ũ ����Ʈ�� �Ʒ� ��ũ��Ʈ�� �����Ѵ�.

```bash
python apps/review-insights/scripts/batch_quality_report.py --appids 2456740 1049590
```

�⺻ ��� ���:

- `apps/review-insights/data/reports/batch_quality_report.json`
- `apps/review-insights/data/reports/batch_quality_report.md`

���� ���� ��Ģ�� `apps/review-insights/docs/normalization-benchmark.md`�� �������� �Ѵ�.

실험용 코호트를 사용하려면 `--cohort-file` 옵션을 함께 사용한다.

```bash
python apps/review-insights/scripts/batch_quality_report.py --cohort-file apps/review-insights/data/reports/experimental_cohort.json
```

특정 appid만 다시 실행하고 싶다면 `--appids`를 같이 붙인다.

```bash
python apps/review-insights/scripts/batch_quality_report.py --cohort-file apps/review-insights/data/reports/experimental_cohort.json --appids 2456740
```
