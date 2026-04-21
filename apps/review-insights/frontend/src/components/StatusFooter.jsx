export default function StatusFooter({ disclaimer, statusLine }) {
  return (
    <footer className="report-footer">
      <p id="disclaimer">{disclaimer || "-"}</p>
      <p id="status-line">{statusLine}</p>
    </footer>
  );
}
