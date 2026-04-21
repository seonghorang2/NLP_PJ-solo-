async function loadJson(url, fallbackMessage) {
  const response = await fetch(url);
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.detail || fallbackMessage);
  }
  return response.json();
}

export async function fetchDemoGames() {
  const payload = await loadJson("/api/games", "게임 목록을 불러오지 못했습니다.");
  const games = Array.isArray(payload?.games) ? payload.games : [];
  return games.filter((item) => item?.report_ready);
}

export async function fetchReport(appid) {
  return loadJson(`/api/games/${appid}/report`, "리포트를 불러오지 못했습니다.");
}
