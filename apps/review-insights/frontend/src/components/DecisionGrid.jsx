export default function DecisionGrid({
  buyTimingSummary,
  recentStateSummary,
  recentStateStatus,
  buyRecommendation,
  generatedAt,
}) {
  return (
    <section className="decision-grid">
      <article className="section-card">
        <h2>지금 사도 될까?</h2>
        <p className="section-body">{buyTimingSummary || "-"}</p>
      </article>
      <article className="section-card">
        <h2>현재 상태</h2>
        <p className="section-body">{recentStateSummary || "-"}</p>
        <p className="section-kicker">{recentStateStatus || "-"}</p>
      </article>
      <article className="section-card">
        <h2>최종 추천</h2>
        <p className="section-body">{buyRecommendation || "-"}</p>
        <p className="section-kicker">{generatedAt || "-"}</p>
      </article>
    </section>
  );
}
