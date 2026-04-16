# 정규화 벤치마크 리포트

- 생성 시각: `2026-04-16T14:06:37.453747+09:00`
- 코호트 크기: `32`
- 처리된 게임 수: `32`
- 건너뛴 게임 수: `0`

## 게임별 요약

| appid | 게임명 | 대표 버킷 | raw | 포함 | 미분류 비율 | 테마 누락 비율 | ambiguity 비율 | notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| 1245620 | ELDEN RING | 소울라이크/하드코어 액션 | 7998 | 4675 | 0.6021 | 0.0513 | 0.4666 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1627720 | P의 거짓 (Lies of P) | 소울라이크/하드코어 액션 | 3999 | 3147 | 0.3889 | 0.0350 | 0.4381 | 카테고리 확장 또는 정규화 사전 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1174180 | Red Dead Redemption 2 | 오픈월드 스토리형 | 7999 | 4652 | 0.5408 | 0.0488 | 0.4231 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1091500 | Cyberpunk 2077 | 오픈월드 스토리형 | 7998 | 5158 | 0.4556 | 0.0551 | 0.4076 | 카테고리 확장 또는 정규화 사전 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 578080 | PUBG: BATTLEGROUNDS | 경쟁 FPS/PVP | 11999 | 4056 | 0.5929 | 0.1519 | 0.2704 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; 규칙 경계 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 730 | Counter-Strike 2 | 경쟁 FPS/PVP | 7996 | 3225 | 0.5603 | 0.1033 | 0.3100 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; 규칙 경계 점검 필요; 한국어 필터 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 252490 | Rust | 생존/크래프팅 | 8000 | 4789 | 0.5907 | 0.1046 | 0.4296 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 892970 | Valheim | 생존/크래프팅 | 7542 | 5062 | 0.4793 | 0.1632 | 0.4182 | 카테고리 확장 또는 정규화 사전 보강 필요; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 413150 | Stardew Valley | 라이프/시뮬레이션 | 7998 | 4791 | 0.6143 | 0.1751 | 0.4616 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 2456740 | inZOI (인조이) | 라이프/시뮬레이션 | 1526 | 1306 | 0.3423 | 0.0773 | 0.4463 | 카테고리 확장 또는 정규화 사전 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요 |
| 230410 | Warframe | 라이브서비스/MMO | 8000 | 5480 | 0.6159 | 0.0453 | 0.5111 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1085660 | 데스티니 가디언즈 | 라이브서비스/MMO | 8000 | 5098 | 0.5430 | 0.0553 | 0.4541 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 289070 | Sid Meier’s Civilization® VI | 전략/경영 | 8000 | 5142 | 0.5541 | 0.2203 | 0.4401 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 294100 | RimWorld | 전략/경영 | 7904 | 5531 | 0.5751 | 0.1287 | 0.4962 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 381210 | Dead by Daylight | 협동/비대칭 멀티 | 8000 | 5204 | 0.6483 | 0.0705 | 0.5269 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 553850 | HELLDIVERS™ 2 | 협동/비대칭 멀티 | 7999 | 5470 | 0.4499 | 0.2459 | 0.4072 | 카테고리 확장 또는 정규화 사전 보강 필요; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 814380 | Sekiro™: Shadows Die Twice - GOTY Edition | 소울라이크/하드코어 액션 | 4000 | 2729 | 0.5548 | 0.0923 | 0.4853 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 374320 | DARK SOULS™ III | 소울라이크/하드코어 액션 | 4000 | 2614 | 0.6362 | 0.0547 | 0.5340 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 292030 | The Witcher 3: Wild Hunt | 오픈월드 스토리형 | 3999 | 2625 | 0.4141 | 0.0758 | 0.3898 | 카테고리 확장 또는 정규화 사전 보강 필요; 규칙 경계 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 271590 | Grand Theft Auto V 레거시 | 오픈월드 스토리형 | 3999 | 1466 | 0.6228 | 0.0866 | 0.2988 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; 규칙 경계 점검 필요; 한국어 필터 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 359550 | 톰 클랜시의 레인보우식스 시즈 | 경쟁 FPS/PVP | 3999 | 2358 | 0.6098 | 0.1107 | 0.4681 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 440 | Team Fortress 2 | 경쟁 FPS/PVP | 4000 | 2009 | 0.6461 | 0.1274 | 0.4183 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 한국어 필터 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 648800 | Raft | 생존/크래프팅 | 4000 | 2589 | 0.4735 | 0.1974 | 0.4120 | 카테고리 확장 또는 정규화 사전 보강 필요; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 346110 | ARK: Survival Evolved | 생존/크래프팅 | 4000 | 2040 | 0.5270 | 0.1564 | 0.3660 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; 규칙 경계 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1222670 | The Sims™ 4 | 라이프/시뮬레이션 | 2666 | 1695 | 0.4802 | 0.0826 | 0.4029 | 카테고리 확장 또는 정규화 사전 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 105600 | Terraria | 라이프/시뮬레이션 | 3999 | 2234 | 0.5971 | 0.1213 | 0.4251 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 570 | Dota 2 | 라이브서비스/MMO | 2400 | 1261 | 0.5726 | 0.2419 | 0.3692 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; 규칙 경계 점검 필요; 한국어 필터 점검 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 582010 | Monster Hunter: World | 라이브서비스/MMO | 3999 | 2431 | 0.5940 | 0.1094 | 0.4679 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1158310 | Crusader Kings III | 전략/경영 | 2099 | 1409 | 0.5905 | 0.0830 | 0.4769 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 236850 | Europa Universalis IV | 전략/경영 | 1537 | 1132 | 0.5292 | 0.0998 | 0.4658 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 1966720 | Lethal Company | 협동/비대칭 멀티 | 4000 | 2339 | 0.5571 | 0.2467 | 0.4270 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |
| 548430 | Deep Rock Galactic | 협동/비대칭 멀티 | 3426 | 2282 | 0.5351 | 0.1626 | 0.4839 | 현재 taxonomy가 게임 표현을 충분히 포착하지 못함; theme pattern 보강 필요; ambiguity 기준 재정의 또는 LLM fallback 설계 보강 필요; 저품질 규칙 또는 장르 특성 점검 필요 |

## 버킷별 실패 패턴 요약

| 대표 버킷 | 게임 수 | 평균 미분류 비율 | 평균 테마 누락 비율 | 평균 ambiguity 비율 | 포함 게임 |
|---|---:|---:|---:|---:|---|
| 경쟁 FPS/PVP | 4 | 0.6023 | 0.1233 | 0.3667 | PUBG: BATTLEGROUNDS, Counter-Strike 2, 톰 클랜시의 레인보우식스 시즈, Team Fortress 2 |
| 라이브서비스/MMO | 4 | 0.5814 | 0.1130 | 0.4506 | Warframe, 데스티니 가디언즈, Dota 2, Monster Hunter: World |
| 라이프/시뮬레이션 | 4 | 0.5085 | 0.1141 | 0.4340 | Stardew Valley, inZOI (인조이), The Sims™ 4, Terraria |
| 생존/크래프팅 | 4 | 0.5176 | 0.1554 | 0.4064 | Rust, Valheim, Raft, ARK: Survival Evolved |
| 소울라이크/하드코어 액션 | 4 | 0.5455 | 0.0583 | 0.4810 | ELDEN RING, P의 거짓 (Lies of P), Sekiro™: Shadows Die Twice - GOTY Edition, DARK SOULS™ III |
| 오픈월드 스토리형 | 4 | 0.5083 | 0.0666 | 0.3798 | Red Dead Redemption 2, Cyberpunk 2077, The Witcher 3: Wild Hunt, Grand Theft Auto V 레거시 |
| 전략/경영 | 4 | 0.5622 | 0.1330 | 0.4698 | Sid Meier’s Civilization® VI, RimWorld, Crusader Kings III, Europa Universalis IV |
| 협동/비대칭 멀티 | 4 | 0.5476 | 0.1814 | 0.4612 | Dead by Daylight, HELLDIVERS™ 2, Lethal Company, Deep Rock Galactic |

## 이상치 요약

- 높은 미분류 비율: `3`건
- 높은 테마 누락 비율: `3`건
- 높은 ambiguity 비율: `3`건
- 부분 수집 게임: `0`건
