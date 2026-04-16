# Report Release Gate

## 목적
- 사용자용 구매 판단 리포트가 릴리즈 기준을 만족하는지 자동 점검한다.
- 점검 기준은 `3초 내 구매판단 가능` 4점 체크리스트를 사용한다.

## 점검 기준 (4점)
1. 핵심 결론 존재 (`headline`, `buy_recommendation`, `buy_timing_summary`)
2. 적합성 정보 존재 (`good_for`, `not_good_for`)
3. 근거 존재 (`evidence_sections.strengths`, `evidence_sections.risks`)
4. 금지 라벨 노출 0 (분류형 라벨 미노출)

## 추가 품질 지표 (점수 외 참고)
- `evidence_mismatch_rate`
  - 카드 기대 stance(강점=positive, 리스크=negative)와
    스니펫 자동 판정 stance가 어긋난 비율
  - 값이 높을수록 카드-근거 정합성 품질이 낮음

## 실행

```bash
python apps/review-insights/scripts/check_report_release_gate.py ^
  --cohort-file apps/review-insights/data/catalog/cohort_v2_32.json ^
  --output apps/review-insights/data/reports/report_release_gate.json ^
  --min-score 4 ^
  --max-unknown-snippet-rate 0.40
```

## 출력
- JSON: `apps/review-insights/data/reports/report_release_gate.json`
- Markdown: `apps/review-insights/data/reports/report_release_gate.md`

## 종료 코드
- `0`: 게이트 통과
- `1`: 게이트 실패

## 추가 보조 게이트
- `unknown_snippet_rate` 상한을 넘으면 점수(4점)가 통과여도 실패 처리
- 기본값: `0.40`
