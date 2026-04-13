"""Minimal API routes for the review-insights backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, HTTPException
except ImportError:  # pragma: no cover - exercised only when FastAPI is missing.
    APIRouter = None
    HTTPException = None

from services.analysis_service import run_and_persist_analysis
from services.comparison_service import compare_analysis_results
from services.steam_reviews import (
    build_unknown_game_metadata,
    fetch_steam_game_metadata,
    fetch_steam_reviews,
    normalize_steam_game_metadata,
    normalize_steam_reviews,
)
from storage.file_store import FileStore

APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = APP_ROOT / "data"
GAME_NAME_KO_OVERRIDES: dict[int, str] = {
    1091500: "사이버펑크 2077",
    1174180: "레드 데드 리뎀션 2",
    1222670: "더 심즈 4",
    252490: "러스트",
    230410: "워프레임",
    1145350: "하데스 II",
    381210: "데드 바이 데이라이트",
    275850: "노 맨즈 스카이",
}


def ingest_reviews_payload(payload: dict[str, Any], data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Run ingestion and analysis from a request payload."""
    appid = payload.get("appid")
    steam_payload = payload.get("steam_payload")
    game_metadata_payload = payload.get("game_metadata_payload")
    review_pages = _parse_review_pages(payload.get("review_pages", "all"))

    if not isinstance(appid, int):
        raise ValueError("appid must be provided as an integer.")

    fetched_from_steam = False
    fetch_stats: dict[str, Any] = {}
    if steam_payload is None:
        steam_payload = fetch_steam_reviews(
            appid,
            max_pages=None if review_pages == "all" else review_pages,
        )
        fetch_stats = steam_payload.get("_fetch_stats", {}) if isinstance(steam_payload, dict) else {}
        fetched_from_steam = True
    elif not isinstance(steam_payload, dict):
        raise ValueError("steam_payload must be provided as an object when supplied.")

    if game_metadata_payload is not None and not isinstance(game_metadata_payload, dict):
        raise ValueError("game_metadata_payload must be provided as an object when supplied.")

    if game_metadata_payload is not None:
        game_metadata = normalize_steam_game_metadata(appid, game_metadata_payload)
    elif fetched_from_steam:
        game_metadata = normalize_steam_game_metadata(appid, fetch_steam_game_metadata(appid))
    else:
        game_metadata = build_unknown_game_metadata(appid)
    output_game_name = _resolve_output_game_name(appid, game_metadata.name, payload)

    raw_reviews = normalize_steam_reviews(appid, steam_payload)
    result, processed_reviews = run_and_persist_analysis(
        raw_reviews,
        appid=appid,
        data_root=data_root,
        game_name=output_game_name,
    )
    store = FileStore(data_root)
    if fetched_from_steam:
        analysis_payload = result.to_dict()
        analysis_payload.update(
            {
                "review_pages": review_pages,
                "fetched_pages": fetch_stats.get("pages_fetched"),
                "fetched_review_count": fetch_stats.get("deduped_review_count"),
                "fetch_timeout_seconds": fetch_stats.get("request_timeout_seconds"),
                "fetch_filter": fetch_stats.get("filter_type"),
                "all_mode_page_cap": fetch_stats.get("all_mode_page_cap"),
                "all_mode_cap_reached": fetch_stats.get("all_mode_cap_reached"),
            }
        )
        store.write_analysis_result(appid, analysis_payload, game_name=output_game_name)

    store.write_game_metadata(appid, game_metadata.to_dict(), game_name=output_game_name)

    return {
        "appid": appid,
        "raw_review_count": len(raw_reviews),
        "processed_review_count": len(processed_reviews),
        "included_review_count": sum(
            1 for review in processed_reviews if review.included_in_analysis
        ),
        "sample_size_tier": result.sample_size_tier,
        "trend_status": result.trend_status,
        "review_pages": review_pages,
        "fetched_pages": fetch_stats.get("pages_fetched") if fetched_from_steam else None,
        "fetched_review_count": fetch_stats.get("deduped_review_count") if fetched_from_steam else None,
        "fetch_timeout_seconds": fetch_stats.get("request_timeout_seconds") if fetched_from_steam else None,
        "fetch_filter": fetch_stats.get("filter_type") if fetched_from_steam else None,
        "all_mode_page_cap": fetch_stats.get("all_mode_page_cap") if fetched_from_steam else None,
        "all_mode_cap_reached": fetch_stats.get("all_mode_cap_reached") if fetched_from_steam else None,
        "metadata_collected": game_metadata.release_stage != "unknown" or bool(game_metadata.genres),
        "price_model": game_metadata.price_model,
        "release_stage": game_metadata.release_stage,
        "output_file_game_name": output_game_name,
    }


def _resolve_output_game_name(
    appid: int,
    metadata_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    explicit_name = payload.get("file_game_name_ko")
    if isinstance(explicit_name, str) and explicit_name.strip():
        return explicit_name.strip()
    if appid in GAME_NAME_KO_OVERRIDES:
        return GAME_NAME_KO_OVERRIDES[appid]
    return metadata_name


def _parse_review_pages(value: Any) -> int | str:
    if value is None:
        return "all"

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "all":
            return "all"
        if normalized.isdigit():
            value = int(normalized)
        else:
            raise ValueError("review_pages must be 'all' or an integer between 1 and 10.")

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("review_pages must be 'all' or an integer between 1 and 10.")
    if value < 1 or value > 10:
        raise ValueError("review_pages must be 'all' or an integer between 1 and 10.")
    return value


def load_analysis_result(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Load a stored analysis result for one game."""
    store = FileStore(data_root)
    return store.read_analysis_result(appid)


def load_raw_reviews(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> list[dict[str, Any]]:
    """Load stored raw review records for one game."""
    store = FileStore(data_root)
    return store.read_raw_reviews(appid)


def load_processed_reviews(
    appid: int,
    data_root: str | Path = DEFAULT_DATA_ROOT,
) -> list[dict[str, Any]]:
    """Load stored processed review records for one game."""
    store = FileStore(data_root)
    return store.read_processed_reviews(appid)


def load_game_metadata(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Load stored game metadata for one game."""
    store = FileStore(data_root)
    return store.read_game_metadata(appid)


def load_comparison_result(
    appid1: int,
    appid2: int,
    data_root: str | Path = DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Load stored artifacts for two games and build a comparison payload."""
    analysis1 = load_analysis_result(appid1, data_root=data_root)
    analysis2 = load_analysis_result(appid2, data_root=data_root)
    raw_reviews1 = load_raw_reviews(appid1, data_root=data_root)
    raw_reviews2 = load_raw_reviews(appid2, data_root=data_root)

    metadata1 = _load_optional_metadata(appid1, data_root=data_root)
    metadata2 = _load_optional_metadata(appid2, data_root=data_root)

    return compare_analysis_results(
        appid1,
        analysis1,
        raw_reviews1,
        metadata1,
        appid2,
        analysis2,
        raw_reviews2,
        metadata2,
    )


def _load_optional_metadata(appid: int, data_root: str | Path) -> dict[str, Any] | None:
    try:
        return load_game_metadata(appid, data_root=data_root)
    except FileNotFoundError:
        return None


if APIRouter is not None:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health():
        """Return a minimal health response."""
        return {"status": "ok"}

    @router.post("/ingest")
    def ingest(payload: dict[str, Any]):
        """Persist and analyze a provided Steam review payload."""
        try:
            return ingest_reviews_payload(payload)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.get("/games/{appid}/analysis")
    def get_analysis(appid: int):
        """Return the stored analysis artifact for an appid."""
        try:
            return load_analysis_result(appid)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"analysis for appid {appid} was not found",
            ) from exc

    @router.get("/games/{appid}/metadata")
    def get_metadata(appid: int):
        """Return stored game metadata for an appid."""
        try:
            return load_game_metadata(appid)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"metadata for appid {appid} was not found",
            ) from exc

    @router.get("/compare")
    def compare_games(appid1: int, appid2: int):
        """Return a conservative comparison payload for two appids."""
        try:
            return load_comparison_result(appid1, appid2)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/games/{appid}/raw")
    def get_raw_reviews(appid: int):
        """Return stored raw reviews for an appid."""
        try:
            return load_raw_reviews(appid)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"raw reviews for appid {appid} were not found",
            ) from exc

    @router.get("/games/{appid}/processed")
    def get_processed_reviews(appid: int):
        """Return stored processed reviews for an appid."""
        try:
            return load_processed_reviews(appid)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"processed reviews for appid {appid} were not found",
            ) from exc
else:  # pragma: no cover - exercised only when FastAPI is missing.
    router = None
