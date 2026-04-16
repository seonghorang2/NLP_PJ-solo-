# 내부 분류용 카테고리 초안 v3 (cohort_v2_32)

## 1) 목적
- 본 문서는 **내부 분류 정확도 개선**을 위한 카테고리 체계를 고정한다.
- 범위는 `cohort_v2_32`(32개 게임)이며, 리포트 노출 문구가 아닌 **분류 엔진 기준**이다.

## 2) 이번 라운드(2차 최소 보강) 적용 내용
- 대상: 신규 16개에서 `included=true && tags=[]` 샘플 상위 표현.
- `categorize.py`에 최소 보강 토큰 15개 추가:
  - `안켜짐`, `싱글코어`
  - `패링`, `구르기`, `자유도`, `보스잡`, `공룡`, `오토체스`
  - `무료로`, `무료다`
  - `팀킬`, `친구`
  - `한국어`, `더빙`
  - `업데이트`
- 반영 파일: `apps/review-insights/backend/analysis/categorize.py`

## 3) 게이트 결과 (동일 32코호트 재집계)
- 기준 지표: `unclassified_ratio (included cap=1200)`
- baseline: `0.5763`
- current: `0.5449`
- delta: `-0.0314`
- 판정: **PASS (감소)**
- 근거 파일:
  - `apps/review-insights/data/reports/cohort_v2_32_unclassified_gate_round2.json`
  - `apps/review-insights/data/reports/batch_quality_report.cohort32.post_round2.json`

## 4) 내부 분류 카테고리 최종 고정안 (v3)

### A. 플레이 경험
- `gameplay`
- `story`
- `graphics`
- `customization`

### B. 진입/학습
- `difficulty`
- `controls`

### C. 기술 안정성
- `performance`
- `bugs`
- `save_progression`

### D. 장기 동기/확장성
- `content_depth`
- `mod_support`
- `building_ux` (내부 분류 전용 유지)

### E. 멀티/공정성
- `multiplayer`
- `balance`

### F. 가격/운영/언어
- `monetization`
- `localization`

## 5) 32코호트 기준 상위 카테고리 스냅샷 (참고)
- `multiplayer`: 11,325
- `gameplay`: 11,227
- `content_depth`: 9,655
- `story`: 6,590
- `monetization`: 5,944

## 6) 운영 규칙 (v3 고정)
- 분류 로직은 결정론 규칙 기반을 우선한다.
- 보강은 루프당 소규모(10~15 표현)만 추가한다.
- 게이트는 동일 코호트/동일 지표로 비교한다.
- 지표가 악화되면 즉시 롤백하고 보강 후보를 재선별한다.

