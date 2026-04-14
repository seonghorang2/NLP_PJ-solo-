# all-mode 운영 정책

## 1. 목적

`review_pages="all"` 수집 정책을 운영 경로 기준으로 고정한다.

---

## 2. 기본 규칙

- all 모드는 운영 수동 실행 시 사용한다.
- 최대 수집 페이지는 200으로 제한한다.
- 요청 timeout 기본값은 20초다.
- 정렬 기준은 최신순(`recent`)이다.

---

## 3. 기록 필드

ingest 응답/분석 메타에 아래 필드를 포함한다.

- `fetched_pages`
- `fetched_review_count`
- `fetch_timeout_seconds`
- `fetch_filter`
- `all_mode_page_cap`
- `all_mode_cap_reached`

---

## 4. 해석 규칙

- `all_mode_cap_reached=true`는 부분 수집으로 해석한다.
- 부분 수집 상태에서도 기존 스냅샷을 덮어쓸지 여부는 운영자가 판단한다.
- refresh check 결과와 함께 해석해 수동 재분석을 결정한다.
