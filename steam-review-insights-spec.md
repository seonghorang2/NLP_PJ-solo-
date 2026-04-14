# Steam Review Insights 제품 명세 (MVP)

## 1. 제품 목적

단일 Steam 게임(appid)의 리뷰를 분석해 리포트를 제공한다.  
사용자 응답 속도를 위해 분석은 오프라인에서 선계산하고, 사용자 경로는 저장 결과 조회만 수행한다.

---

## 2. 제품 범위

- 단일 게임 리포트
- 오프라인 리뷰 수집 및 분석
- 전처리, 카테고리 분류, 키워드/테마 추출, 트렌드 분석, 요약
- 사용자용 구매 전 의사결정 리포트

비범위:

- 게임 비교 기능
- 사용자 요청 시 실시간 대량 재분석
- 추천 시스템

---

## 3. 운영 모드

### 3.1 실서비스 목표 구조

1. 특정 게임 리뷰를 오프라인 파이프라인으로 분석 후 저장
2. 사용자 조회 시 저장된 분석 결과로 리포트 생성
3. 신규 리뷰가 n개 이상 누적되면 재분석 트리거
4. 갱신된 분석 결과로 리포트 재생성

### 3.2 현재 데모 구현 구조

- 전체 Steam 게임 선분석은 하지 않는다.
- 고정 코호트 게임만 운영한다.
- 자동 재분석 트리거는 구현하지 않는다.
- `refresh check`에서 `현재 리뷰 수 - 마지막 분석 리뷰 수`를 계산해 `업데이트 필요`만 판정한다.
- 실제 재분석 실행은 운영자가 수동으로 수행한다.

---

## 4. 아키텍처 구성 요소

1. Game Catalog  
- 데모 대상 게임 목록 및 운영 파라미터 관리  
- 필드 예: `appid`, `name`, `enabled_for_demo`, `refresh_threshold_n`, `last_review_count`, `last_analyzed_at`

2. Offline Pipeline  
- 수집 -> 전처리 -> LLM fallback -> 집계 -> 저장

3. Snapshot Store  
- `analysis_snapshots`, `report_outputs` 성격의 최신 결과 저장소

4. Report API  
- 저장된 스냅샷 조회 기반 리포트 응답

5. Admin Refresh Tool  
- refresh check 수행, 수동 재분석 실행

---

## 5. 전처리 및 LLM 단계 정의

### Step 1. Raw Ingestion (LLM 없음)

- 원문 리뷰 저장
- 메타데이터 저장

### Step 2. Deterministic Core Preprocess (LLM 없음)

- 텍스트 정규화(공백/기호)
- 한글 비율 계산
- 길이/반복문자/기호 기반 저품질 1차 판정
- 욕설-only 1차 판정
- 명확한 카테고리 1차 태깅
- 시간/플레이타임 버킷 생성
- **명백한 케이스 hard decision만 처리**

### Step 3. Ambiguity Detection (LLM 없음)

- 애매한 리뷰 플래그 설정
- 예: 경계 한국어 비율, 욕설+의미 신호 공존, 카테고리 경합, 반어 의심, 낮은 rule confidence

### Step 4. Selective LLM Fallback (LLM 사용)

- 애매한 subset만 입력
- 포함/제외 보조 판정
- 멀티라벨 보조 판정
- canonical theme 보조 정규화
- 반어/풍자 해석 보조

### Step 5. Final Decision Merge (LLM 없음)

- rule 결과와 llm 결과 병합
- **최종 포함/제외, 최종 태그, 최종 테마 확정은 이 단계에서만 수행**
- 판정 흔적 저장

---

## 6. LLM 호출 게이트

LLM은 아래를 모두 만족할 때만 호출한다.

1. 의미 신호 1개 이상 존재
- 예: 의미 있는 불만/칭찬, 분석 가치가 있는 내용

2. 불확실성 신호 1개 이상 존재
- 예: 낮은 rule confidence, 카테고리 충돌, 반어/풍자 의심, 사전 미매칭 테마

단일 조건만으로는 호출하지 않는다.

### LLM 하드 제외 구간

아래 케이스는 LLM 호출 금지:

- 극히 낮은 `hangul_ratio`
- 명백한 저품질 리뷰
- 명백한 욕설-only 리뷰
- 빈 입력, 기호-only 입력

---

## 7. Confidence와 병합 규칙

- `rule_confidence`: 결정론 점수 기반(길이, 언어비율, 키워드 강도 등)
- `llm_confidence`: 모델 출력값(정규화된 범위)

최종 병합 규칙:

- `rule_confidence >= threshold` 이면 rule 결정 우선
- 그렇지 않으면 llm 결정을 사용
- `final_decision_source`를 항상 명시

---

## 8. 출력 계약 (Processed Review 필수 필드)

- `rule_decision`
- `rule_confidence`
- `llm_invoked`
- `llm_decision` (nullable)
- `llm_confidence` (nullable)
- `final_decision_source` (`rule | llm`)
- `final_decision`

---

## 9. 운영 안전장치 (MVP)

- 배치당 `max_llm_reviews`
- 호출당 timeout
- 재시도 제한(`max 2`)
- 스키마 검증 실패 시 rule 결과 유지
- 동일 텍스트 캐시로 중복 호출 방지

---

## 10. 우선순위

1. 정확성
2. 단순성
3. 유지보수성
4. 관심사의 분리
5. 소비자 리포트로서 빠른 가독성 UX
