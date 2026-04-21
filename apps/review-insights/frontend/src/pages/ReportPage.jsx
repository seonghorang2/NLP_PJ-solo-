import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchDemoGames, fetchReport } from "../api/reportApi";
import DecisionGrid from "../components/DecisionGrid";
import EvidenceSection from "../components/EvidenceSection";
import FitGrid from "../components/FitGrid";
import StatusFooter from "../components/StatusFooter";
import StrengthRiskSection from "../components/StrengthRiskSection";
import Topbar from "../components/Topbar";
import {
  buyBadgeClass,
  formatGeneratedAt,
  normalizeEvidenceSections,
  recommendationLabel,
  recentStateLabel,
  toList,
} from "../utils/reportMappers";

export default function ReportPage() {
  const [games, setGames] = useState([]);
  const [selectedAppid, setSelectedAppid] = useState("");
  const [report, setReport] = useState(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [statusLine, setStatusLine] = useState("게임 목록 준비 중...");

  const openReport = useCallback(async (appidValue) => {
    const numericAppid = Number(appidValue);
    if (!numericAppid) {
      setStatusLine("리포트 대상 게임을 선택해 주세요.");
      return;
    }

    setIsLoadingReport(true);
    setStatusLine("구매 판단 리포트를 불러오는 중입니다...");
    try {
      const payload = await fetchReport(numericAppid);
      setReport(payload);
      setStatusLine("불러오기 완료");
    } catch (error) {
      setStatusLine(error?.message || "리포트 로드에 실패했습니다.");
    } finally {
      setIsLoadingReport(false);
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function bootstrap() {
      setStatusLine("게임 목록 준비 중...");
      try {
        const loadedGames = await fetchDemoGames();
        if (isCancelled) {
          return;
        }

        setGames(loadedGames);
        if (loadedGames.length === 0) {
          setSelectedAppid("");
          setStatusLine("표시 가능한 게임이 없습니다.");
          return;
        }

        const firstAppid = String(loadedGames[0].appid);
        setSelectedAppid(firstAppid);
        await openReport(firstAppid);
      } catch (error) {
        if (!isCancelled) {
          setStatusLine(error?.message || "초기화에 실패했습니다.");
        }
      }
    }

    bootstrap();
    return () => {
      isCancelled = true;
    };
  }, [openReport]);

  const display = report?.report_display ?? {};
  const game = report?.game ?? {};
  const recommendation = display.buy_recommendation || "";
  const recentState = display.recent_state || {};
  const evidenceSections = useMemo(() => normalizeEvidenceSections(report), [report]);

  const badgeClass = `buy-badge ${buyBadgeClass(recommendation)}`;
  const goodFor = toList(display.good_for);
  const notGoodFor = toList(display.not_good_for);
  const topStrengths = toList(display.top_strengths);
  const topRisks = toList(display.top_risks);

  async function handleSubmit(event) {
    event.preventDefault();
    await openReport(selectedAppid);
  }

  return (
    <main className="report-shell">
      <Topbar
        games={games}
        selectedAppid={selectedAppid}
        onSelectChange={setSelectedAppid}
        onSubmit={handleSubmit}
        isLoadingReport={isLoadingReport}
      />

      <section className="hero-card">
        <div className="hero-meta">
          <p className="game-title">
            {game.name || (report?.appid ? `appid ${report.appid}` : "게임을 선택하면 리포트가 표시됩니다")}
          </p>
          <span className={badgeClass}>{recommendationLabel(recommendation)}</span>
        </div>
        <h1 className="headline">
          {display.headline || "많은 리뷰의 합의 신호를 바탕으로 구매 결정을 빠르게 정리합니다."}
        </h1>
      </section>

      <DecisionGrid
        buyTimingSummary={display.buy_timing_summary}
        recentStateSummary={recentState.summary}
        recentStateStatus={`상태: ${recentStateLabel(recentState.status)}`}
        buyRecommendation={recommendationLabel(recommendation)}
        generatedAt={formatGeneratedAt(report?.generated_at)}
      />

      <FitGrid goodFor={goodFor} notGoodFor={notGoodFor} />

      <StrengthRiskSection strengths={topStrengths} risks={topRisks} />

      <EvidenceSection
        positiveBlocks={evidenceSections.loved}
        negativeBlocks={evidenceSections.complained}
      />

      <StatusFooter disclaimer={report?.disclaimer} statusLine={statusLine} />
    </main>
  );
}
