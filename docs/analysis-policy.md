# Review Insights Analysis Policy

## 1. 정책 목적

본 문서는 분석 파이프라인의 판정 규칙, LLM 호출 규칙, 최종 병합 규칙을 고정한다.  
기준은 “오프라인 선분석 + 조회 전용 서빙 + 수동 재분석”이다.

---

## 2. 범위 정책

- 단일 게임 리포트만 제공한다.
- 게임 비교 기능은 제공하지 않는다.
- 사용자 조회 경로의 실시간 Steam/LLM 호출을 금지한다.
- 수집/전처리/LLM fallback/집계는 운영 경로에서만 수행한다.

---

## 3. 단계별 판정 정책

### Step 1. Raw Ingestion

- 원문/메타데이터 저장
- LLM 미사용

### Step 2. Deterministic Core Preprocess

- 규칙 기반 정규화/필터링/1차 태깅
- hard decision(명백한 포함/제외)만 처리
- LLM 미사용

### Step 3. Ambiguity Detection

- 경계 케이스 탐지 및 ambiguity flag 부여
- LLM 미사용

### Step 4. Selective LLM Fallback

- 애매한 subset만 호출
- 포함/제외 및 태깅 보조

### Step 5. Final Decision Merge

- rule/llm 결과 병합
- 최종 판정은 이 단계에서만 확정
- LLM 미사용

---

## 4. LLM 호출 정책

### 4.1 호출 조건 (AND)

아래 두 조건을 동시에 만족할 때만 LLM 호출:

1. 의미 신호 1개 이상
2. 불확실성 신호 1개 이상

단일 조건 트리거는 호출하지 않는다.

### 4.2 하드 제외 구간

아래는 LLM 호출 금지:

- 극히 낮은 한글 비율
- 명백한 저품질
- 명백한 욕설-only
- 빈 텍스트/기호-only

---

## 5. Confidence/병합 정책

- `rule_confidence`: 결정론 점수 기반
- `llm_confidence`: 모델 출력 기반 정규화 값

병합 규칙:

- `rule_confidence >= threshold` -> rule 우선
- 그 외 -> llm 판정 사용
- `final_decision_source`를 항상 저장

---

## 6. 출력 계약 정책 (필수)

각 processed review는 아래 필드를 반드시 포함한다.

- `rule_decision`
- `rule_confidence`
- `llm_invoked`
- `llm_decision` (nullable)
- `llm_confidence` (nullable)
- `final_decision_source` (`rule | llm`)
- `final_decision`

---

## 7. 운영 안전장치 정책

- `max_llm_reviews` (배치당 상한)
- LLM 호출 timeout
- retry limit 최대 2회
- 스키마 불일치 시 rule fallback
- 동일 텍스트 캐시 적용

---

## 8. refresh 판정 정책 (데모)

- `delta = current_review_count - last_review_count`
- `delta >= n` -> `needs_refresh`
- `delta < n` -> `up_to_date`
- 데모에서는 수동 재분석만 수행한다.

---

## 9. 변경 관리

다음 변경 시 본 문서를 반드시 갱신한다.

- LLM 게이트 조건
- confidence 계산/threshold
- 병합 규칙
- 출력 필드 계약
- 운영 안전장치 파라미터
