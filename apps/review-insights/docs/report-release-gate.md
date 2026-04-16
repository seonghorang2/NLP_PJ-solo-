# Report Release Gate

## 목적
- 사용자용 구매 판단 리포트가 릴리즈 기준을 만족하는지 자동 점검한다.
- 점검 기준은 `3초 내 구매판단 가능` 4점 체크리스트를 사용한다.

## 점검 기준 (4점)
1. 핵심 결론 존재 (`headline`, `buy_recommendation`, `buy_timing_summary`)
2. 적합성 정보 존재 (`good_for`, `not_good_for`)
3. 근거 존재 (`evidence_sections.strengths`, `evidence_sections.risks`)
4. 금지 라벨 노출 0 (분류형 라벨 미노출)

## 실행

```bash
python apps/review-insights/scripts/check_report_release_gate.py ^
  --cohort-file apps/review-insights/data/catalog/cohort_v2_32.json ^
  --output apps/review-insights/data/reports/report_release_gate.json ^
  --min-score 4
```

## 출력
- JSON: `apps/review-insights/data/reports/report_release_gate.json`
- Markdown: `apps/review-insights/data/reports/report_release_gate.md`

## 종료 코드
- `0`: 게이트 통과
- `1`: 게이트 실패

