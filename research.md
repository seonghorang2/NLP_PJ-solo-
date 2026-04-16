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

### 6.3 근거 판정 LLM (judge-only)

파일: `services/evidence_judge_llm.py`

역할:
- 근거 후보(블록별 최대 6~8개) 중에서 stance/theme 일치도가 높은 스니펫만 최종 선택
- **문장 재작성은 하지 않고 판정/선별만 수행**
- 불일치 후보는 다음 후보로 교체

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
- `USE_LLM_EVIDENCE_JUDGE`
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

---

## 13. 전처리 Markup Cleaning 0단계 규칙

목표:
- HTML/BBCode가 포함된 리뷰에서 분석 노이즈를 줄인다.
- 원문 증거 보존을 위해 `review_text` 원문은 유지하고, 분석용 텍스트에만 적용한다.

적용 순서:
1. HTML entity decode
2. HTML 태그 제거
3. BBCode 제거
4. 공백 정리

안전 규칙:
- `<3` 같은 일반 텍스트는 태그로 오인 제거하지 않는다.
- `script/style` 블록은 통째 제거한다.

---

## 14. 경계 케이스 10개 테스트 시나리오

1. `진짜 재밌다 <3`  
   - 기대: `<3` 보존, 텍스트 유지
2. `2 < 3 이고 5 > 1`  
   - 기대: 수학 비교 표현 보존
3. `<b>전투</b>는 좋고 <br> 최적화는 별로`  
   - 기대: 태그 제거 후 문장 보존
4. `<script>alert('x')</script> 게임은 재밌음`  
   - 기대: script 블록 제거, 본문만 남김
5. `[h3]장점[/h3] 타격감 좋음`  
   - 기대: BBCode 제거, 본문 유지
6. `[url=https://example.com]링크[/url] 때문에 튕김`  
   - 기대: BBCode 제거, 의미 텍스트 유지
7. `코드: <div class='x'>if(a<b){...}</div>`  
   - 기대: 태그만 제거, 코드 텍스트 최대한 보존
8. `&lt;b&gt;가짜태그&lt;/b&gt;`  
   - 기대: decode 후 태그 처리 정책에 맞게 정리
9. `<<< 진짜 구림 >>>`  
   - 기대: 태그 오인 제거 없이 일반 텍스트 유지
10. `<p>[b]혼합[/b] 마크업</p>`  
   - 기대: HTML + BBCode 모두 제거, 본문만 유지

---

## 15. 적용 후 부작용 점검(최소 지표)

비교 방법:
- 동일 appid / 동일 raw 데이터 기준으로 적용 전후를 비교한다.

필수 비교 지표:
- `included_count` 변화량
- `low_quality_count` 변화량

판단 기준(초기안):
- `included_count` 급감(예: 10% 이상 감소) 시 과필터링 의심
- `low_quality_count` 급증 시 마크업 제거 규칙 오작동 의심

점검 절차:
1. 적용 전 `analysis/processed`에서 두 지표 기록
2. markup cleaning 적용 후 동일 지표 재측정
3. 변화가 큰 샘플 20개 수동 확인
