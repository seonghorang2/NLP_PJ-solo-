# Steam 리뷰 기반 구매 의사결정 리포트 시스템 리서치

작성일: 2026-04-15  
대상: 이 프로젝트를 처음 보는 개발자/기획자

---

## 1. 한 줄 정의

이 시스템은 **Steam 게임 리뷰를 오프라인에서 미리 분석**해 두고,  
사용자가 게임을 선택하면 **즉시 구매 의사결정 리포트**를 보여주는 서비스다.

핵심 질문:
- 지금 사도 되는가?
- 나와 맞는 게임인가?
- 감수해야 할 리스크는 무엇인가?

---

## 2. 시스템 구성 요약

### 2.1 오프라인 파이프라인 (무거운 작업)

파일: `apps/review-insights/backend/pipeline/offline_pipeline.py`

1. Steam 리뷰/메타데이터 수집
2. 결정론적 전처리
3. 분석 집계(카테고리/테마/트렌드)
4. 리포트 재료 정제(선택적 LLM)
5. 리포트 JSON 생성
6. 결과 파일 저장

### 2.2 온라인 조회 (가벼운 작업)

파일: `apps/review-insights/backend/api/routes.py`

- 저장된 snapshot/report만 조회
- 사용자 요청에서 Steam API/전처리/LLM 실행 없음

---

## 3. 데이터 흐름

저장 경로(`apps/review-insights/data`):
- `raw/`: 수집 원문 리뷰
- `processed/`: 전처리 결과
- `analysis/`: 집계 결과 + 운영 메타
- `metadata/`: 게임 메타데이터
- `report/`: 최종 사용자 리포트
- `catalog/demo_games.json`: 데모 게임 목록

---

## 4. 전처리(결정론적) 원칙

파일: `analysis/preprocess.py`, `analysis/rules.py`, `analysis/categorize.py`

규칙:
- 저품질 리뷰 제외
- 욕설-only 리뷰 제외
- 한국어 비율이 낮은 리뷰 제외
- 멀티라벨 카테고리 태깅
- `rule_decision`, `rule_confidence`, `final_decision_source` 등 흔적 보존

주의:
- 이 단계는 설명 가능한 규칙 기반이 중심이다.

---

## 5. 분석/집계 단계

파일: `services/analysis_service.py`

산출:
- 카테고리별 언급량/부정비율/최근 추세
- 상위 테마
- 요약 문장

결과는 `AnalysisResult` 형태로 저장된다.

---

## 6. LLM 사용 지점 (중요)

### 6.1 리포트 재료 정제 LLM (신규 구조)

파일: `services/report_material_refiner.py`

기존(변경 전):
- 전처리 중 애매한 리뷰를 LLM으로 include/exclude 보조 판정

변경 후:
- **분석 집계 완료 후**
- **리포트 쓰임새가 높은 리뷰 최대 50개만 선별**
- LLM으로 `refined_text`(1~4문장) 생성
- 이 정제 재료를 리포트 생성 단계에 전달

선별 기준(다중 키):
1. category/theme 정보 유무
2. 플레이타임
3. 작성자 리뷰 수
4. 텍스트 길이
5. 최신성

운영 안전장치:
- `max_llm_reviews`
- timeout/retry
- 동일 텍스트 캐시
- schema invalid/저신뢰 시 deterministic fallback

### 6.2 리포트 생성 LLM

파일: `services/report_writer_llm.py`

역할:
- `report_plan`
- `report_display`
- `evidence_sections`

을 JSON 계약으로 생성/보정한다.

### 6.3 근거 문장 압축 LLM

파일: `services/evidence_snippet_llm.py`

역할:
- evidence 스니펫을 읽기 좋은 짧은 문장으로 정리

### 6.4 한국어 교정 LLM

파일: `services/korean_report_proofreader.py`

역할:
- 조사/띄어쓰기/문법 보정
- 의미 변경 없이 표현 품질 개선

---

## 7. 리포트 생성 구조

파일: `services/report_view.py`

생성 결과:
- `report_plan`: 어떤 근거로 어떤 섹션을 구성할지
- `report_display`: 사용자에게 바로 보여줄 핵심 문구
- `evidence_sections`: 강점/리스크별 근거 블록

중요:
- evidence는 원문 덤프가 아니라
  - 제목
  - 왜 중요한지
  - 2~3개 근거 스니펫
  구조로 제공된다.

---

## 8. API 구조

사용자 read-only:
- `GET /api/games`
- `GET /api/games/{appid}/report`
- `GET /api/games/{appid}/analysis`
- `GET /api/games/{appid}/metadata`

관리자 수동 실행:
- `POST /api/admin/ingest`

---

## 9. 데모 운영 원칙

- 단일 게임 리포트 중심
- 고정 카탈로그 게임만 제공
- 자동 재분석 대신 수동 실행
- “신규 리뷰 n개 이상이면 재분석 필요”는 정책/판정 로직 중심

---

## 10. 실행 방법

오프라인 실행:

```bash
python apps/review-insights/scripts/run_offline_pipeline.py --appid 578080 --review-pages all --use-llm-fallback
```

서버 실행:

```bash
uvicorn app:app --app-dir apps/review-insights/backend --reload
```

브라우저:
- `http://localhost:8000`

---

## 11. 환경변수

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (기본 `gpt-4o-mini`)
- `USE_LLM_REPORT_WRITER`
- `USE_LLM_EVIDENCE_COMPRESSION`
- `USE_LLM_REPORT_PROOFREAD`

---

## 12. 현재 구조의 장점/주의점

장점:
- 사용자 응답 속도가 빠름
- 사용자 경로 안정성 높음(외부 API 실패 영향 축소)
- LLM 비용 통제 가능

주의:
- 파일 기반 저장이라 대규모 운영에는 한계
- 오프라인 파이프라인을 누가/언제 돌릴지 운영 룰 필요
- 품질 튜닝은 규칙 사전 + 리포트 재료 정제가 핵심

