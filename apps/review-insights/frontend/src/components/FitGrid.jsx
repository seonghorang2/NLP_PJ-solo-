function BulletList({ values }) {
  const items = Array.isArray(values) ? values : [];
  if (items.length === 0) {
    return (
      <ul className="bullet-list">
        <li>데이터가 충분하지 않습니다.</li>
      </ul>
    );
  }

  return (
    <ul className="bullet-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

export default function FitGrid({ goodFor, notGoodFor }) {
  return (
    <section className="fit-grid">
      <article className="section-card">
        <h2>잘 맞는 플레이어</h2>
        <BulletList values={goodFor} />
      </article>
      <article className="section-card">
        <h2>주의가 필요한 플레이어</h2>
        <BulletList values={notGoodFor} />
      </article>
    </section>
  );
}
