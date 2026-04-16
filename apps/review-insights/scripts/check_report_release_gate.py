"""Release gate checker for buyer-facing report quality."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
DATA_DIR = APP_DIR / "data"
DEFAULT_COHORT_FILE = DATA_DIR / "catalog" / "cohort_v2_32.json"
DEFAULT_OUTPUT = DATA_DIR / "reports" / "report_release_gate.json"

FORBIDDEN_LABELS = (
    "조작 / 규칙 학습 난이도",
    "전투 손맛 / 액션 호평",
    "스토리 / 서사 몰입",
    "스토리/서사 몰입",
    "최적화 문제",
    "일반 버그",
    "가격 / 과금 불만",
    "가격/ 과금 불만",
    "DLC / 확장팩 언급",
    "반복 / 목적성 부족",
    "매칭 / 서버 문제",
    "밸런스 불만",
    "번역/현지화 품질",
    "건축 조작 불편",
    "콘텐츠 부족",
    "세이브 / 진행 유실",
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_report_path(appid: int) -> Path | None:
    report_dir = DATA_DIR / "report"
    exact = report_dir / f"{appid}.json"
    if exact.exists():
        return exact
    named = sorted(
        path
        for path in report_dir.glob("*.json")
        if path.name.startswith(f"{appid}(") and path.name.endswith(".json")
    )
    if named:
        return max(named, key=lambda path: path.stat().st_mtime)
    loose = sorted(report_dir.glob(f"{appid}*.json"))
    if loose:
        return max(loose, key=lambda path: path.stat().st_mtime)
    return None


def collect_text_targets(report_payload: dict[str, Any]) -> list[str]:
    report_display = dict(report_payload.get("report_display", {}) or {})
    evidence_sections = dict(report_payload.get("evidence_sections", {}) or {})

    targets: list[str] = []
    if isinstance(report_display.get("headline"), str):
        targets.append(str(report_display.get("headline", "")))

    for item in list(report_display.get("top_strengths", []) or []):
        if isinstance(item, dict) and isinstance(item.get("title"), str):
            targets.append(str(item.get("title", "")))
    for item in list(report_display.get("top_risks", []) or []):
        if isinstance(item, dict) and isinstance(item.get("title"), str):
            targets.append(str(item.get("title", "")))

    for stance_key in ("strengths", "risks"):
        for block in list(evidence_sections.get(stance_key, []) or []):
            if isinstance(block, dict) and isinstance(block.get("title"), str):
                targets.append(str(block.get("title", "")))

    return targets


def count_forbidden_label_exposure(texts: list[str]) -> tuple[int, list[dict[str, str]]]:
    exposure_count = 0
    hits: list[dict[str, str]] = []
    for text in texts:
        normalized = " ".join(str(text).split()).strip()
        if not normalized:
            continue
        for label in FORBIDDEN_LABELS:
            if label in normalized:
                exposure_count += 1
                hits.append({"text": normalized, "label": label})
                break
    return exposure_count, hits


def evaluate_report(appid: int, game_name: str, report_payload: dict[str, Any]) -> dict[str, Any]:
    report_display = dict(report_payload.get("report_display", {}) or {})
    evidence_sections = dict(report_payload.get("evidence_sections", {}) or {})

    buy_recommendation = str(report_display.get("buy_recommendation", "")).strip()
    headline = str(report_display.get("headline", "")).strip()
    timing = str(report_display.get("buy_timing_summary", "")).strip()
    good_for = list(report_display.get("good_for", []) or [])
    not_good_for = list(report_display.get("not_good_for", []) or [])

    strengths = list(evidence_sections.get("strengths", []) or [])
    risks = list(evidence_sections.get("risks", []) or [])

    decision_core_ready = bool(buy_recommendation and headline and timing)
    fit_ready = bool(good_for and not_good_for)
    evidence_ready = bool(strengths and risks)

    text_targets = collect_text_targets(report_payload)
    forbidden_count, forbidden_hits = count_forbidden_label_exposure(text_targets)

    quick_score = 0
    quick_score += 1 if decision_core_ready else 0
    quick_score += 1 if fit_ready else 0
    quick_score += 1 if evidence_ready else 0
    quick_score += 1 if forbidden_count == 0 else 0

    return {
        "appid": appid,
        "game_name": game_name,
        "decision_core_ready": decision_core_ready,
        "fit_ready": fit_ready,
        "evidence_ready": evidence_ready,
        "forbidden_label_exposure_count": forbidden_count,
        "forbidden_label_hits_sample": forbidden_hits[:5],
        "quick_decision_score_4": quick_score,
    }


def load_cohort(cohort_file: Path) -> list[dict[str, Any]]:
    payload = load_json(cohort_file)
    if isinstance(payload, dict) and isinstance(payload.get("cohort"), list):
        return list(payload.get("cohort", []))
    if isinstance(payload, list):
        return list(payload)
    raise ValueError("cohort file must be a list or object with 'cohort' field")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 리포트 릴리즈 게이트 결과",
        "",
        f"- 생성 시각: `{payload['generated_at']}`",
        f"- 코호트 파일: `{payload['cohort_file']}`",
        f"- 평가 대상: `{payload['evaluated_game_count']}`",
        f"- 누락 리포트: `{payload['missing_report_count']}`",
        f"- 최소 통과 점수: `{payload['min_score']}`",
        f"- 전체 통과: `{payload['gate_passed']}`",
        "",
        "| appid | 게임 | 점수(4) | 핵심결론 | 적합성 | 근거 | 금지라벨 | 통과 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in payload.get("results", []):
        lines.append(
            "| {appid} | {game_name} | {score} | {core} | {fit} | {ev} | {forbidden} | {passed} |".format(
                appid=row.get("appid"),
                game_name=row.get("game_name"),
                score=row.get("quick_decision_score_4"),
                core="Y" if row.get("decision_core_ready") else "N",
                fit="Y" if row.get("fit_ready") else "N",
                ev="Y" if row.get("evidence_ready") else "N",
                forbidden=row.get("forbidden_label_exposure_count"),
                passed="Y" if row.get("passed") else "N",
            )
        )

    if payload.get("missing_reports"):
        lines.extend(["", "## 누락 리포트", ""])
        for item in payload["missing_reports"]:
            lines.append(f"- `{item['appid']}` {item['game_name']}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run release gate checks for report outputs.")
    parser.add_argument(
        "--cohort-file",
        type=Path,
        default=DEFAULT_COHORT_FILE,
        help="Path to cohort json file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output JSON",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=4,
        help="Minimum quick_decision_score_4 required to pass",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cohort = load_cohort(args.cohort_file)

    results: list[dict[str, Any]] = []
    missing_reports: list[dict[str, Any]] = []

    for item in cohort:
        appid = int(item["appid"])
        game_name = str(item.get("game_name") or appid)
        report_path = resolve_report_path(appid)
        if report_path is None:
            missing_reports.append({"appid": appid, "game_name": game_name})
            continue
        report_payload = load_json(report_path)
        row = evaluate_report(appid, game_name, report_payload)
        row["report_path"] = str(report_path)
        row["passed"] = int(row["quick_decision_score_4"]) >= int(args.min_score)
        results.append(row)

    gate_passed = (
        bool(results)
        and not missing_reports
        and all(bool(row.get("passed")) for row in results)
    )

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "cohort_file": str(args.cohort_file),
        "min_score": int(args.min_score),
        "evaluated_game_count": len(results),
        "missing_report_count": len(missing_reports),
        "missing_reports": missing_reports,
        "gate_passed": gate_passed,
        "results": results,
    }

    write_json(args.output, payload)
    write_markdown(args.output.with_suffix(".md"), payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "markdown_output": str(args.output.with_suffix(".md")),
                "evaluated_game_count": len(results),
                "missing_report_count": len(missing_reports),
                "gate_passed": gate_passed,
            },
            ensure_ascii=False,
        )
    )
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

