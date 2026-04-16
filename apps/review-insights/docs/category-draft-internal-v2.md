# 내부 분류용 카테고리 초안 v2

## 1) 이번 v2 변경 요약
- `cohort_v1`의 라이브서비스/MMO 버킷 대상을 `1599340(Lost Ark)`에서 `1085660(Destiny 2)`로 교체했다.
- `tags=[]` 비율 상위 5개 게임(413150, 289070, 553850, 578080, 294100)에 대해 규칙 사전 보강 루프 1회를 적용했다.
- 최신 집계 기준으로 코호트 16개 전부 `processed` 데이터가 존재한다.

## 2) 근거 파일
- 코호트: `apps/review-insights/data/catalog/cohort_v1.json`
- 보강 루프 요약: `apps/review-insights/data/reports/cohort_v1_rule_reinforcement_loop_summary.json`
- v2 집계: `apps/review-insights/data/reports/cohort_v1_category_aggregate_snapshot_v2.json`

## 3) 보강 루프 결과 (상위 5개 tags=[] 개선)

| appid | 게임 | 전 | 후 | delta |
|---:|---|---:|---:|---:|
| 413150 | Stardew Valley | 0.7491 | 0.6414 | -0.1077 |
| 289070 | Sid Meier's Civilization VI | 0.7219 | 0.5626 | -0.1593 |
| 553850 | HELLDIVERS 2 | 0.6759 | 0.4755 | -0.2004 |
| 578080 | PUBG: BATTLEGROUNDS | 0.6635 | 0.6191 | -0.0444 |
| 294100 | RimWorld | 0.6614 | 0.5849 | -0.0765 |

## 4) v2 상위 내부 카테고리 (고빈도)

| 순위 | 카테고리 키 | 집계 건수 |
|---|---|---:|
| 1 | `gameplay` | 7,814 |
| 2 | `multiplayer` | 7,456 |
| 3 | `content_depth` | 6,803 |
| 4 | `difficulty` | 6,576 |
| 5 | `story` | 5,573 |
| 6 | `monetization` | 4,630 |
| 7 | `bugs` | 3,922 |
| 8 | `performance` | 3,099 |
| 9 | `graphics` | 2,672 |
| 10 | `mod_support` | 2,296 |

## 5) v2 상위 내부 테마 (고빈도)

| 순위 | canonical theme | 집계 건수 |
|---|---|---:|
| 1 | 스토리 / 서사 몰입 | 3,731 |
| 2 | 일반 버그 | 2,693 |
| 3 | 부정행위 / 보안 이슈 | 1,773 |
| 4 | 최적화 문제 | 1,708 |
| 5 | 조작 / 규칙 학습 난이도 | 1,651 |
| 6 | DLC / 확장팩 언급 | 1,488 |
| 7 | 밸런스 불만 | 1,377 |
| 8 | 반복 / 목적성 부족 | 1,202 |
| 9 | 그래픽 / 비주얼 호평 | 1,154 |
| 10 | 난이도 / 진입장벽 | 1,077 |

## 6) 내부 분류 구조 v2 제안

### A. 핵심 플레이 경험
- 키: `gameplay`, `story`, `graphics`, `customization`
- 대표 테마: 전투 손맛/액션 호평, 탐험/월드 경험, 스토리/서사 몰입

### B. 입문/조작성
- 키: `difficulty`, `controls`
- 대표 테마: 난이도/진입장벽, 조작/규칙 학습 난이도, UI/입력 불편

### C. 기술 안정성
- 키: `performance`, `bugs`, `save_progression`
- 대표 테마: 최적화 문제, 일반 버그, 실행 불가/튕김

### D. 장기 유지력
- 키: `content_depth`, `building_ux`, `mod_support`
- 대표 테마: 콘텐츠 부족, 반복/목적성 부족, 모드 지원/호환 문제

### E. 멀티/공정성
- 키: `multiplayer`, `balance`
- 대표 테마: 매칭/서버 문제, 부정행위/보안 이슈, 밸런스 불만

### F. 가치/운영 체감
- 키: `monetization`, `localization`
- 대표 테마: 가격/과금 불만, DLC/확장팩 언급, 번역/현지화 이슈

## 7) 남은 리스크
- `tags=[]` 비율이 아직 높은 게임이 남아 있다(특히 578080, 294100).
- 의미: 표현 사전 보강을 1회 더 돌리면 개선 여지가 크다.

## 8) 다음 루프 우선순위
1. `578080`, `294100` 미분류 상위 샘플 100개 재라벨링
2. `multiplayer`, `content_depth`, `difficulty` 표현 사전 2차 보강
3. 같은 코호트로 재집계 후 v3 초안 생성
