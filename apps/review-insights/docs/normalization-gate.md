# Normalization Gate

정규화 루프 종료 시 아래 게이트를 체크한다.

- `included_drop_rate <= 0.10`
- `unc_ratio_delta < 0`

위 조건 중 하나라도 실패하면 `rollback.required=true`로 판정한다.

## 실행 예시

```bash
python apps/review-insights/scripts/check_normalization_gate.py ^
  --baseline apps/review-insights/data/reports/batch_quality_report.v3.baseline.json ^
  --current apps/review-insights/data/reports/batch_quality_report.json ^
  --max-included-drop-rate 0.10 ^
  --output apps/review-insights/data/reports/normalization_gate_result.json ^
  --fail-on-gate
```

## 결과 파일

- `apps/review-insights/data/reports/normalization_gate_result.json`

