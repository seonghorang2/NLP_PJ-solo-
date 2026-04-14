# 전체 아키텍처 가이드

## 1. 모노레포 원칙

- 서비스는 `apps/<service>/`로 분리한다.
- 현재 구현 대상은 `apps/review-insights/`다.
- 타 팀 서비스와 코드/데이터 경계를 섞지 않는다.

---

## 2. review-insights 목표 구조

```text
Offline Plane
  Game Catalog
  -> Review Ingestion
  -> Preprocess/LLM Fallback/Analysis
  -> Snapshot Store

Serving Plane
  Report API
  -> Snapshot Read
  -> Report Response

Ops Plane
  Refresh Check
  -> needs_refresh 판정
  -> 수동 재분석 실행
```

---

## 3. 핵심 구성 요소

1. Game Catalog
- 데모 대상 게임 목록
- 게임별 임계치 n 관리

2. Offline Pipeline
- 리뷰 수집/전처리/분류/요약/저장

3. Snapshot Store
- 최신 분석 결과와 메타 저장

4. Report API
- 조회 전용 응답

5. Admin Refresh Tool
- refresh check
- 수동 재분석

---

## 4. 운영 원칙

- 조회 경로는 실시간 분석을 수행하지 않는다.
- 분석 freshness는 refresh check + 수동 실행으로 관리한다.
- 데모는 전체 Steam이 아닌 고정 코호트만 운영한다.
