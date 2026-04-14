# review-insights 전환 계획 (문서 기준)

## 1. 전환 목표

- 사용자 경로: snapshot 조회 전용
- 운영 경로: refresh check + 수동 재분석
- LLM: 애매한 subset에만 제한적 사용

---

## 2. 핵심 설계 원칙

1. 전처리 코어와 LLM enrichment를 분리한다.
2. hard decision은 Step 2에서만 처리한다.
3. final decision merge는 Step 5에서만 처리한다.
4. LLM은 2조건 게이트(의미+불확실성)로 제한한다.
5. 출력 계약과 운영 안전장치를 고정한다.

---

## 3. 파이프라인 계획

### Step 1. Raw Ingestion

- 원문 저장
- 메타데이터 저장

### Step 2. Deterministic Core Preprocess

- 텍스트 정규화
- 한글 비율 계산
- 저품질/욕설-only 1차 판정
- 1차 카테고리 태깅
- hard decision 처리

### Step 3. Ambiguity Detection

- ambiguity flags 생성
- rule confidence 산출

### Step 4. Selective LLM Fallback

- 게이트 통과 subset만 LLM 호출
- 포함/제외/카테고리/theme 보조 판정

### Step 5. Final Decision Merge

- rule+llm 병합
- 최종 필드 확정
- 판정 흔적 저장

---

## 4. LLM 게이트 계획

호출 조건:

- 의미 신호 1개 이상 AND 불확실성 신호 1개 이상

하드 제외:

- 극저 한글 비율
- 명백한 저품질
- 명백한 욕설-only
- 빈/기호-only

---

## 5. 병합/계약 계획

### 5.1 confidence

- rule_confidence: 규칙 점수
- llm_confidence: 모델 출력

### 5.2 merge

- `rule_confidence >= threshold`: rule 우선
- 그 외: llm 사용

### 5.3 필수 필드

- `rule_decision`
- `rule_confidence`
- `llm_invoked`
- `llm_decision`
- `llm_confidence`
- `final_decision_source`
- `final_decision`

---

## 6. 운영 안전장치 계획

- `max_llm_reviews`
- timeout
- retry max 2
- schema invalid -> rule fallback
- identical text cache

---

## 7. 데모 운영 계획

- 고정 코호트 게임만 운영
- refresh check로 `needs_refresh`만 판정
- 수동 재분석으로 snapshot 갱신
- `delta < n`이면 스킵하고 기존 snapshot 유지

---

## 8. 완료 기준

- 문서 전반에서 단계 분리/게이트/병합 규칙이 일관된다.
- LLM 과호출 가능 문구가 남지 않는다.
- 수동 운영 모델이 runbook과 충돌하지 않는다.
