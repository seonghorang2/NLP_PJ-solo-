import { formatSnippetForDisplay } from "../utils/reportMappers";

function EvidenceColumn({ title, blocks, emptyMessage }) {
  const classes = [
    "evidence-section",
    blocks.length === 0 ? "is-empty" : "",
    blocks.length === 1 ? "is-single" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classes}>
      <h3>{title}</h3>
      <div className="evidence-grid">
        {blocks.length === 0 ? <p className="placeholder">{emptyMessage}</p> : null}
        {blocks.map((block, blockIndex) => (
          <article className="evidence-card" key={`${block.title}-${blockIndex}`}>
            <h3>{block.title || "-"}</h3>
            <p className="evidence-why">{block.whyItMatters || "-"}</p>
            <ul className="evidence-snippets">
              {block.evidenceSnippets.map((snippet, snippetIndex) => (
                <li key={`${snippet}-${snippetIndex}`}>{formatSnippetForDisplay(snippet)}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </article>
  );
}

export default function EvidenceSection({ positiveBlocks, negativeBlocks }) {
  return (
    <section className="section-card">
      <h2>구매 근거</h2>
      <div className="evidence-sections">
        <EvidenceColumn
          title="강점 근거"
          blocks={positiveBlocks}
          emptyMessage="표시할 긍정 근거 리뷰가 없습니다."
        />
        <EvidenceColumn
          title="리스크 근거"
          blocks={negativeBlocks}
          emptyMessage="표시할 부정 근거 리뷰가 없습니다."
        />
      </div>
    </section>
  );
}
