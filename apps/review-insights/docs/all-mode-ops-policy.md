# all-mode 운영 정책

## 목적

`review_pages="all"` 요청의 기본 동작과 상한 정책을 명확히 정의한다.

## 고정 정책 (개발/운영 공통)

- `all` 모드 기본값은 유지한다.
- 단, 실제 수집은 **최대 200페이지**까지만 수행한다.
- 페이지당 요청 timeout 기본값은 `20초`다.
- 정렬 기준은 `recent`(최신순)를 유지한다.

## 응답 메타데이터

`/api/ingest` 응답에는 아래 필드를 포함한다.

- `fetched_pages`: 실제 수집한 페이지 수
- `fetched_review_count`: 중복 제거 후 raw 리뷰 수
- `fetch_timeout_seconds`: 페이지 요청 timeout
- `fetch_filter`: 정렬/필터 기준
- `all_mode_page_cap`: all 모드 페이지 상한(현재 200)
- `all_mode_cap_reached`: 상한 도달 여부

동일한 ingest로 저장된 `GET /api/games/{appid}/analysis` 결과에도 `all_mode_page_cap`, `all_mode_cap_reached`를 포함한다.

## 운영 해석 규칙

- `all_mode_cap_reached=true`이면 "전체 리뷰 완전 수집"이 아니라 "상한 내 부분 수집"으로 해석한다.
- 대시보드 상태 패널/로그에서 cap 도달 여부를 반드시 확인한다.
