# 전체 아키텍처 제안

## 1. 목적

이 문서는 현재 저장소를 여러 팀이 함께 사용할 수 있는 구조로 정리하기 위한 상위 아키텍처 기준을 정의한다.

현재 확인된 제품 방향은 최소 두 가지다.

- `review-insights`
  - 1개 또는 2개 게임을 선택해 리뷰를 분석하는 내부 도구
- `game-recommendation`
  - 전체 리뷰를 요약하고 추천에 활용하려는 별도 시스템

두 제품은 Steam 리뷰를 공통 입력으로 사용할 수 있지만, 제품 목표와 파이프라인이 다르므로 코드베이스 경계를 분리해야 한다.

---

## 2. 최상위 원칙

1. 저장소는 모노레포로 운영한다.
2. 제품별 코드는 `apps/` 아래에 분리한다.
3. 공통화는 실제 중복이 확인된 뒤에만 진행한다.
4. 초기에는 제품 경계를 보호하는 것이 코드 재사용보다 우선이다.
5. 데이터, 테스트, 문서도 앱 내부에 가능한 한 함께 둔다.
6. LLM은 필요한 앱 내부에서만 선택적으로 사용하고, 저장소 공통 플랫폼으로 성급하게 추상화하지 않는다.

---

## 3. 권장 최상위 구조

```text
NLP_PJ/
  AGENTS.md
  steam-review-insights-spec.md
  plan.md

  apps/
    review-insights/
      backend/
      frontend/
      data/
      tests/
      docs/

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

---

## 4. 왜 제품 기준 분리가 필요한가

### 4.1 `review-insights`의 특성

- 1~2개 게임 선택
- 수동 분석 실행
- 결정론적 리뷰 필터링
- 카테고리/키워드/트렌드/요약
- 내부 대시보드 중심

### 4.2 `game-recommendation`의 특성

- 전체 또는 대규모 리뷰 입력 가능성
- 추천/랭킹/서빙 로직 가능성
- 배치 처리 또는 사전 계산 가능성
- 다른 데이터 모델과 평가 방식 필요 가능성

### 4.3 결론

둘은 입력 소스는 일부 겹칠 수 있어도, 핵심 도메인 모델과 서비스 경계는 다르다.

따라서 다음을 분리해야 한다.

- 백엔드 코드
- 데이터 저장 경로
- 테스트
- 앱 문서
- 프론트엔드

---

## 5. 공통화 원칙

`shared/`는 다음 기준을 통과한 것만 받는다.

1. 최소 두 앱에서 실제 중복이 발생했다.
2. 두 앱의 요구사항 차이가 작다.
3. 추출 후 오히려 이해가 쉬워진다.
4. 공통 모듈이 앱별 속도를 늦추지 않는다.

초기에는 아래 항목을 `shared/`로 옮기지 않는다.

- 분석 파이프라인
- 저장소 구현
- 서비스 오케스트레이션
- 프론트 컴포넌트
- 앱 전용 데이터 모델
- LLM 프롬프트 및 판정 로직

초기에 `shared/`로 둘 수 있는 후보는 매우 제한적이다.

- 문서
- 팀 공통 규칙
- 매우 단순한 Steam 응답 정규화 타입

---

## 6. 데이터 경계 원칙

각 앱은 자기 데이터 디렉터리를 가진다.

예시:

```text
apps/review-insights/data/
apps/game-recommendation/data/
```

이렇게 하면 다음 충돌을 피할 수 있다.

- 파일명 충돌
- 저장 포맷 충돌
- 전처리 기준 충돌
- 동일 appid에 대한 다른 파이프라인 결과 충돌

---

## 7. 문서 경계 원칙

문서도 두 층으로 나눈다.

### 루트 문서

- 저장소 공통 원칙
- 앱 간 경계
- 최상위 아키텍처

### 앱 문서

- 앱의 API
- 앱의 데이터 흐름
- 앱의 실행 방법
- 앱의 테스트 방법

예시:

```text
docs/architecture.md
docs/analysis-policy.md
apps/review-insights/docs/runbook.md
apps/review-insights/docs/api.md
```

---

## 8. 현재 서비스에 대한 적용 방침

지금 구현 대상은 `apps/review-insights/` 아래에만 둔다.

이번 MVP에서 만들 코드와 데이터는 모두 이 범위 안에 한정한다.

- `apps/review-insights/backend/`
- `apps/review-insights/frontend/`
- `apps/review-insights/data/`
- `apps/review-insights/tests/`
- `apps/review-insights/docs/`

`game-recommendation` 앱에는 현재 코드나 구조를 강제하지 않는다.
필요한 경우 빈 디렉터리 또는 자리 표시 수준으로만 남긴다.

### 8.1 LLM 사용 방침

`review-insights` 앱은 LLM을 사용할 수 있지만, 역할은 제한적이어야 한다.

- 기본 전처리는 규칙 기반으로 유지한다.
- LLM은 애매한 리뷰 subset에 대한 보조 판정 계층으로만 둔다.
- LLM 프롬프트, 캐시, 판정 정책은 앱 내부에 유지한다.
- LLM 사용은 공통 플랫폼 전제 없이 앱 단위로 독립 운영한다.
- `review-insights` 앱은 단일 우선순위 점수를 공통 플랫폼처럼 정의하지 않는다.
- 대신 카테고리별 주요 이슈 신호를 앱 내부에서 집계하고, 최종 판단은 내부 사용자가 수행한다.

### 8.2 재현성과 비용 원칙

- 전체 리뷰에 대한 무차별 LLM 호출은 피한다.
- 프롬프트 버전을 고정하고 기록한다.
- JSON schema 기반 출력만 수용한다.
- 캐시를 통해 같은 입력에 대한 중복 호출을 줄인다.
- 규칙 기반 결과와 LLM 결과를 함께 저장해 감사 가능성을 유지한다.

---

## 9. 단계별 적용 순서

1. 저장소 구조를 `apps/` 중심으로 재정의한다.
2. 현재 MVP 계획서의 경로를 `apps/review-insights/` 기준으로 변경한다.
3. `review-insights` 앱 전용 상세 구조 문서를 만든다.
4. 실제 구현은 `review-insights` 앱 안에서만 시작한다.
5. 이후 팀 간 중복이 생기면 그때 `shared/` 후보를 검토한다.

---

## 10. 최종 권장안

현재 시점의 가장 보수적이고 유지보수하기 쉬운 선택은 다음과 같다.

- 저장소는 모노레포
- 제품은 `apps/` 아래로 분리
- `review-insights`와 `game-recommendation`은 독립 앱
- 공통화는 나중에
- 이번 구현은 `review-insights`에만 한정

이 방향이 MVP 규칙, 팀 협업 안정성, 향후 확장성을 가장 균형 있게 만족한다.
