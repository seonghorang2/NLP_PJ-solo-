# 파일명 정책 (Storage Naming)

`apps/review-insights/data/` 하위 저장 파일은 기본적으로 아래 형식을 사용한다.

- `raw/{appid}({game_name_ko}).json`
- `processed/{appid}({game_name_ko}).json`
- `analysis/{appid}({game_name_ko}).json`
- `metadata/{appid}({game_name_ko}).json`

설명:

- 파일 가독성을 위해 appid 뒤에 괄호 형태로 게임명을 붙인다.
- API 조회(`GET /api/games/{appid}/...`)는 여전히 appid 기준으로 동작한다.
- 경로 해석 시 `appid(게임명).json`을 우선 조회하고, 필요하면 `appid.json`도 호환 처리한다.
