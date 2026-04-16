# Demo 운영 체크리스트

## 목적
- 데모 시연 전, 오프라인 재생성 → 품질 게이트 → UI 확인 순서를 고정한다.
- 게이트 통과 게임만 `demo_games.json`에서 노출 상태를 유지한다.

## 1) 오프라인 리포트 재생성 (raw 재수집 없음)
- 대상: 데모 코호트 게임
- 실행 방식: 저장된 `metadata/analysis/processed`를 사용해 `report`만 재생성
- 확인 포인트:
  - `apps/review-insights/data/report/*.json` 생성 시간 갱신
  - 핵심 섹션(`headline`, `buy_recommendation`, `evidence_sections`) 존재

## 2) 릴리즈 게이트 실행
```bash
python apps/review-insights/scripts/check_report_release_gate.py \
  --cohort-file apps/review-insights/data/reports/_tmp_demo6_cohort.json \
  --output apps/review-insights/data/reports/report_release_gate.demo6.json \
  --min-score 4 \
  --max-unknown-snippet-rate 0.40
```

- 통과 기준:
  - `quick_decision_score_4 >= 4`
  - `evidence_unknown_snippet_rate <= 0.40`
  - 금지 라벨 노출 없음

## 3) 노출 대상 확정
- 게이트 `passed=true` 게임:
  - `demo_games.json`의 `enabled_for_demo=true` 유지
- 게이트 `passed=false` 게임:
  - `enabled_for_demo=false`로 전환
  - 재튜닝 대상 목록으로 분리

## 4) LLM Evidence Judge A/B 점검
- 목적: `USE_LLM_EVIDENCE_JUDGE=true` 효과(unknown/mismatch 개선) 측정
- 산출물:
  - `apps/review-insights/data/reports/evidence_judge_ab_demo6.json`
- 필수 점검:
  - `openai_key_set=true`
  - `judge_available=true`
  - `delta.avg_unknown_rate < 0` 또는 `delta.avg_mismatch_rate < 0`

## 5) UI 최종 확인
- 서버 실행:
```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```
- 확인 항목:
  - 노출 게임 목록이 `demo_games.json`과 일치
  - 강점/리스크 근거 블록에 빈 섹션 없음
  - 근거 스니펫이 HTML 태그 없이 읽기 가능한 형태

## 6) 실패 시 처리 원칙
- unknown 비율 초과: 근거 후보 교체/stance 힌트 보강 후 리포트 재생성
- 금지 라벨 노출: report_view 치환 레이어 보강 후 재생성
- LLM A/B 불가: 키/모델 설정 확인 후 재측정
