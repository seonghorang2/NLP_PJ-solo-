# 내부 분류용 카테고리 초안 v1

## 1) 목적
- 이 문서는 `cohort_v1` 실데이터를 기반으로 내부 분석 파이프라인에서 사용할 분류 축 초안을 정리한다.
- 사용자 노출 문구가 아니라, 분석/집계 정확도와 유지보수성을 우선한 내부 분류 기준이다.

## 2) 데이터 근거
- 코호트: `apps/review-insights/data/catalog/cohort_v1.json`
- 1차 수집 요약: `apps/review-insights/data/reports/cohort_v1_round1_ingest_summary.json`
- 2차 재수집 요약: `apps/review-insights/data/reports/cohort_v1_round2_resample_summary.json`
- 집계 스냅샷: `apps/review-insights/data/reports/cohort_v1_category_aggregate_snapshot.json`

## 3) 수집 결과 요약
- `cohort_v1` 16개 중 15개 수집 성공
- 실패: `1599340 (Lost Ark)` - Steam appdetails 응답 실패
- 2차 재수집 후 대부분 `target cap(2000/3000)` 달성
- 예외: `2456740 (inZOI)`는 현재 필터 기준 가용 리뷰 한계로 `included=1306`에서 종료(`exhausted`)

## 4) 상위 고빈도 내부 카테고리 (집계 기준)

| 순위 | 카테고리 키 | 집계 건수 | 비중(%) |
|---|---|---:|---:|
| 1 | `difficulty` | 4,531 | 15.07 |
| 2 | `multiplayer` | 3,834 | 12.75 |
| 3 | `content_depth` | 3,246 | 10.80 |
| 4 | `story` | 3,228 | 10.74 |
| 5 | `gameplay` | 2,665 | 8.86 |
| 6 | `bugs` | 2,131 | 7.09 |
| 7 | `monetization` | 1,918 | 6.38 |
| 8 | `graphics` | 1,580 | 5.26 |
| 9 | `performance` | 1,576 | 5.24 |
| 10 | `mod_support` | 1,340 | 4.46 |

## 5) 상위 고빈도 테마 (내부 canonical theme)

| 순위 | 테마 | 집계 건수 |
|---|---|---:|
| 1 | 스토리 / 서사 몰입 | 2,192 |
| 2 | 조작 / 규칙 학습 난이도 | 1,464 |
| 3 | 일반 버그 | 1,378 |
| 4 | 부정행위 / 보안 이슈 | 1,251 |
| 5 | 최적화 문제 | 940 |
| 6 | 밸런스 불만 | 778 |
| 7 | 반복 / 목적성 부족 | 697 |
| 8 | 난이도 / 진입장벽 | 674 |
| 9 | DLC / 확장팩 언급 | 674 |
| 10 | 그래픽 / 비주얼 호평 | 663 |

## 6) 내부 분류 구조 제안 (v1)

### A. 기술 안정성
- 포함 키: `bugs`, `performance`, `save_progression`
- 대표 테마: 일반 버그, 최적화 문제, 실행 불가/튕김, 저장/세이브 손실

### B. 입문/조작성
- 포함 키: `difficulty`, `controls`
- 대표 테마: 난이도/진입장벽, 튜토리얼/온보딩 부족, 조작/규칙 학습 난이도, UI/입력 불편

### C. 핵심 플레이 경험
- 포함 키: `gameplay`, `story`, `graphics`
- 대표 테마: 전투 손맛/액션 호평, 탐험/월드 경험, 스토리/서사 몰입, 그래픽/비주얼 호평

### D. 장기 유지력
- 포함 키: `content_depth`, `building_ux`
- 대표 테마: 콘텐츠 부족, 반복/목적성 부족, 상호작용/생동감 부족

### E. 멀티 신뢰성
- 포함 키: `multiplayer`, `balance`
- 대표 테마: 매칭/서버 문제, 부정행위/보안 이슈, 밸런스 불만

### F. 가치/확장성
- 포함 키: `monetization`, `mod_support`, `customization`, `localization`
- 대표 테마: 가격/과금 불만, 모드 지원/호환 문제, 커스터마이징 호평, 번역/현지화 이슈

## 7) 품질 이슈 및 해석
- `included 대비 tags=[]` 비율이 높다(코호트 가중 평균 약 0.59).
- 의미:
  - 리뷰량(cap) 확대만으로는 분류 커버리지가 충분히 개선되지 않음
  - 다음 루프는 수집량 증가보다 규칙 사전/패턴 보강이 우선

## 8) 다음 내부 작업 우선순위
1. `unclassified_included` 상위 샘플 라벨링(버킷별 100개)
2. `difficulty/multiplayer/content_depth` 우선으로 규칙 사전 보강
3. 재집계 후 `tags=[]` 비율 재측정(개선폭 기준: -5%p 이상)
