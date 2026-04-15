# Steam 리뷰 리포트 시스템 쉽게 이해하기 (research.md)

작성일: 2026-04-15  
대상: 이 프로젝트를 처음 보는 개발자/기획자

---

## 1. 이 시스템이 하는 일 (한 줄 요약)

이 서비스는 **Steam 게임 리뷰를 미리(오프라인) 분석해 저장해 두고**, 사용자가 게임을 선택하면 **저장된 결과를 바로 보여주는 구매 판단 리포트 서비스**입니다.

---

## 2. 먼저 용어부터 쉽게 정리

- `오프라인 파이프라인`: 운영자가 수동으로 돌리는 분석 작업
- `온라인 조회`: 사용자가 화면에서 리포트만 보는 작업
- `Raw 리뷰`: Steam에서 가져온 원본 리뷰
- `Processed 리뷰`: 전처리 규칙을 통과하면서 태그가 붙은 리뷰
- `Analysis`: Processed 리뷰를 집계해서 만든 통계/요약
- `Report`: 사용자가 읽기 쉬운 최종 구매 판단 문서
- `LLM fallback`: 규칙으로 애매한 리뷰만 LLM으로 보조 판단하는 단계

---

## 3. 전체 구조 (중요)

현재 구조는 아래처럼 **2개 경로가 완전히 분리**되어 있습니다.

1. 운영 경로(무거운 작업)
- Steam API 호출
- 전처리/분석/리포트 생성
- 파일 저장

2. 사용자 경로(가벼운 작업)
- 저장된 파일 읽기
- 화면에 리포트 렌더링

즉, 사용자가 버튼을 눌렀다고 Steam API를 다시 부르거나, LLM 분석을 새로 돌리지 않습니다.

---

## 4. 실제 동작 순서

## 4.1 운영자(오프라인) 실행 순서

기준 코드: `apps/review-insights/backend/pipeline/offline_pipeline.py`

1. Steam에서 리뷰/메타데이터를 수집
- 함수: `fetch_steam_reviews()`, `fetch_steam_game_metadata()`
- 기본값:
  - 언어: `koreana`
  - 정렬: `recent` (최신순)
  - `all` 모드 최대 200페이지

2. 원본 형식을 내부 표준 형식으로 변환
- `RawReview`, `GameMetadata`로 변환

3. 규칙 기반 전처리
- 텍스트 정규화
- 한글 비율 계산
- 저품질/욕설-only/비한국어 제외
- 카테고리 태깅
- 애매함 플래그(`ambiguity_flags`) 부여
- 규칙 confidence 계산

4. 선택적 LLM fallback
- 오직 애매한 리뷰 subset만 호출
- 호출 상한: `max_llm_reviews` (기본 50)
- confidence 미달이면 규칙 결과 유지
- schema 이상이면 규칙 결과 유지

5. 분석 집계
- 카테고리별 언급량/부정비율/최근추세
- 테마 추출
- 요약 문장 생성

6. 구매 판단 리포트 생성
- `report_plan` + `report_display` + `evidence_sections`
- 무료 게임/유료 게임 추천 문구 분리
- 한국어 교정(규칙 + 선택적 LLM)

7. 파일 저장
- `data/raw`
- `data/processed`
- `data/analysis`
- `data/metadata`
- `data/report`

---

## 4.2 사용자(온라인) 조회 순서

기준 코드: `apps/review-insights/backend/api/routes.py`, `frontend/app.js`

1. `/api/games`로 게임 목록 조회
2. 사용자가 게임 선택
3. `/api/games/{appid}/report` 조회
4. 저장된 리포트 JSON을 화면에 즉시 렌더링

핵심:
- 사용자 경로에서는 Steam fetch 없음
- 사용자 경로에서는 전처리/분석 없음
- 사용자 경로에서는 리뷰 LLM 분류 없음

---

## 5. 전처리 규칙 (MVP 핵심)

기준 코드: `analysis/preprocess.py`, `analysis/rules.py`, `analysis/categorize.py`

리뷰 한 건마다 아래를 수행합니다.

1. 텍스트 정리
2. 한글 비율 계산
3. 제외 판정
- `exclude_low_quality`
- `exclude_profanity_only`
- `exclude_non_korean` (한글 비율 0.20 미만)
4. 포함 리뷰는 카테고리 멀티태그
5. 애매성 플래그
6. `rule_confidence` 계산

추가 규칙:
- 포함됐는데 카테고리 태그가 비어 있으면 `unclassified_included` 플래그를 붙임

---

## 6. LLM이 들어가는 지점 (정확히)

## 6.1 리뷰 전처리 fallback LLM

파일: `services/llm_classifier.py`, `analysis/llm_fallback.py`

역할:
- 규칙으로 애매한 리뷰를 include/exclude + category/theme 보조 판정

안전장치:
- 호출 수 제한
- timeout/retry
- confidence 임계치
- 실패 시 규칙 결과 유지

## 6.2 리포트 생성 LLM

파일: `services/report_writer_llm.py`

역할:
- 리포트의 문장/섹션 품질 개선
- `report_plan`, `report_display`를 JSON 계약에 맞게 생성

## 6.3 근거 문장 압축 LLM

파일: `services/evidence_snippet_llm.py`

역할:
- 긴 리뷰를 1~4문장 핵심 근거로 압축

## 6.4 한국어 교정 LLM

파일: `services/korean_report_proofreader.py`

역할:
- 조사/띄어쓰기/문법 보정
- 의미를 바꾸지 않게 길이 변화 비율로 안전검증

---

## 7. 데이터 모델 요약

기준 코드: `backend/models/schemas.py`

## 7.1 RawReview

- 리뷰 원문 + 추천/비추천 + 작성시간 + 플레이시간 + 작성자 리뷰수

## 7.2 ProcessedReview

- Raw + 전처리 결과
- `included_in_analysis`
- `rule_decision`, `rule_confidence`
- `llm_invoked`, `llm_decision`, `llm_confidence`
- `final_decision_source`, `final_decision`
- `category_tags`, `canonical_theme`

## 7.3 AnalysisResult

- 표본 크기 단계
- 추세 상태
- 카테고리별 신호(`issue_signals`)
- 요약 문장

---

## 8. 리포트 JSON 구조 (사용자 화면용)

기준 코드: `services/report_writer_llm.py`, `services/report_view.py`

핵심 3개:

1. `report_plan`
- 추천 판단 축, 섹션 개수, 우선 테마

2. `report_display`
- headline
- buy_recommendation
- buy_timing_summary
- good_for / not_good_for
- top_strengths / top_risks
- recent_state

3. `evidence_sections`
- `strengths[]`, `risks[]`
- 각 블록은 제목/의미/설명/근거 스니펫 포함

---

## 9. API 구조

## 9.1 사용자용 read-only API

- `GET /api/games`
- `GET /api/games/{appid}/report`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`
- `GET /api/games/{appid}/raw` (디버그)
- `GET /api/games/{appid}/processed` (디버그)

## 9.2 운영자용 API

- `POST /api/admin/ingest`

제한:
- `demo_games.json`에 등록된 appid만 허용

---

## 10. 프론트엔드 화면 구조

기준 코드: `frontend/index.html`, `frontend/app.js`

현재 화면 구성:

1. 게임 선택
2. 헤드라인 + 추천 배지
3. 지금 사도 될지(타이밍)
4. 현재 상태
5. 최종 추천
6. 잘 맞는 유저 / 주의할 유저
7. 강점 카드 / 리스크 카드
8. 강점 근거 / 리스크 근거 리뷰

즉, 분석 대시보드보다 **구매 의사결정 리포트** 형태에 맞춰져 있습니다.

---

## 11. 실제 실행 방법

## 11.1 오프라인 분석 실행

```bash
python apps/review-insights/scripts/run_offline_pipeline.py ^
  --appid 3551340 ^
  --review-pages all ^
  --use-llm-fallback
```

## 11.2 서버 실행

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

## 11.3 브라우저 확인

- `http://localhost:8000`

---

## 12. 환경변수(자주 쓰는 것)

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (기본 `gpt-4o-mini`)
- `USE_LLM_REPORT_WRITER` (기본 true)
- `USE_LLM_EVIDENCE_COMPRESSION` (기본 true)
- `USE_LLM_REPORT_PROOFREAD` (기본 true)
- `REPORT_PROOFREAD_MAX_LLM_TEXTS` (기본 24)

---

## 13. 현재 데모 게임 목록

기준 파일: `apps/review-insights/data/catalog/demo_games.json`

- 2456740 inZOI
- 1174180 Red Dead Redemption 2
- 1245620 ELDEN RING
- 578080 PUBG: BATTLEGROUNDS
- 413150 Stardew Valley
- 3551340 Football Manager 26

---

## 14. 테스트 현황

2026-04-15 기준 실행 결과:

- `python -m unittest discover -s apps/review-insights/tests`
- 결과: **58개 테스트 통과**

---

## 15. 지금 구조의 장점/주의점

## 장점

- 사용자 속도가 빠름(읽기 전용)
- 비용 통제 쉬움(LLM 호출이 오프라인에 집중)
- 문제 추적 쉬움(파일 산출물 확인 가능)

## 주의점

- 파일 기반이라 대규모 트래픽에는 한계
- 리포트 품질은 전처리 규칙/테마 사전 품질에 영향 받음
- 오프라인 작업을 수동으로 돌려야 최신 상태 유지

---

## 16. 최종 요약

이 프로젝트는 “사용자가 요청할 때마다 분석하는 서비스”가 아니라,  
**운영자가 미리 분석해 둔 결과를 사용자에게 빠르게 보여주는 구매 판단 리포트 시스템**입니다.

핵심은 다음 2개입니다.

1. 무거운 작업은 오프라인으로
2. 사용자 경로는 읽기 전용으로

이 원칙이 지금 코드 전반에 반영되어 있습니다.

