# Report Material Refiner 명세 (MVP)

작성일: 2026-04-15  
대상 서비스: `apps/review-insights`

## 1. 목적

기존의 “전처리 단계 LLM fallback” 대신,  
**분석 집계 완료 후 리포트 쓰임새가 높은 리뷰만 선별(최대 50개)하여 LLM으로 정제**한다.

정제된 리뷰 재료만 `report_writer_llm`(6.2 단계)에 전달해,
리포트 문구의 구체성/일관성/가독성을 높인다.

---

## 2. 적용 위치

- 오프라인 파이프라인 내부의 **분석 이후 단계**에만 적용
- 사용자 요청 경로에서는 실행하지 않음
- 실시간 Steam 호출/실시간 LLM 호출 없음

파이프라인 순서(변경 후):
1. Raw Ingestion
2. Deterministic Preprocess
3. Analysis Aggregation
4. **Report Material Refiner (신규)**
5. Report Writer LLM
6. Report Output 저장

---

## 3. 리뷰 선별 규칙 (Top 50)

선별 대상:
- `included_in_analysis == true` 리뷰만

우선순위 정렬(단일 점수 합산이 아니라 다중 키 정렬):
1. `category_tags` 존재 여부
2. `canonical_theme` 존재 여부
3. `playtime_at_review_hours` (높을수록 우선)
4. `num_reviews` (높을수록 우선)
5. 텍스트 길이(가독 가능한 길이)
6. 최신성(`timestamp_created`)

균형 규칙:
- 긍정(`voted_up=true`) / 부정(`voted_up=false`)을 가능한 한 반반으로 우선 추출
- 부족한 쪽은 다른 쪽으로 채움

---

## 4. LLM 출력 스키마

리뷰 1건당 JSON:

```json
{
  "refined_text": "1~4문장, 의미 보존, 구매 의사결정에 도움되는 요약 근거",
  "stance": "positive | negative | mixed",
  "confidence": 0.0
}
```

검증 규칙:
- `refined_text`: 비어있지 않은 문자열, 문장 수 1~4
- `stance`: enum 값만 허용
- `confidence`: 0.0~1.0

검증 실패/저신뢰 처리:
- schema invalid 또는 `confidence < llm_min_confidence`이면
  - LLM 결과 폐기
  - 규칙 기반 fallback 요약문 사용

---

## 5. 운영 안전장치

- `max_llm_reviews` (기본 50)
- 호출 timeout
- retry limit (기본 2)
- 동일 텍스트 캐시 (중복 호출 방지)
- LLM unavailable 시 deterministic fallback으로 계속 진행

---

## 6. 저장 아티팩트

### 6.1 analysis snapshot 내 메타

`data/analysis/<appid(...).json>`에 아래 필드 기록:

- `report_material_refiner.enabled`
- `report_material_refiner.max_llm_reviews`
- `report_material_refiner.llm_min_confidence`
- `report_material_refiner.material_count`
- `report_material_refiner.stats`

### 6.2 report 생성 입력 재료

오프라인 실행 시 메모리 상 `report_materials`를 `report_view`로 전달:
- `review_id`
- `refined_text`
- `stance`
- `confidence`
- `category_tags`
- `canonical_theme`
- `llm_used`
- `utility_rank`

---

## 7. report_view 연동 규칙

- evidence 구성 시 `review_id`가 매칭되면 원문 대신 `refined_text`를 우선 사용
- `stance`가 있으면 긍정/부정 분류에 우선 사용
- 없으면 기존 규칙(`voted_up` + 키워드)로 fallback

---

## 8. 채택 게이트 (A/B)

대상 게임: `578080`, `413150`

비교 축:
- A안: 기존 구조(전처리 fallback)
- B안: 신규 구조(집계 후 report material refiner)

판단 지표:
1. 리포트 품질
   - evidence 블록의 theme-stance 일치율
   - 빈 블록 비율
2. 시간
   - 오프라인 총 소요시간
   - LLM 호출 시간 비중
3. 비용
   - 호출 건수
   - 대략 토큰 사용량

채택 기준(권장):
- 품질 개선이 확인되고
- 시간/비용 증가가 운영 허용 범위 이내일 때 채택

