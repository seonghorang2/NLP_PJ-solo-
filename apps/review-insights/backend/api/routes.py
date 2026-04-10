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


def ingest_reviews_payload(payload: dict[str, Any], data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Run ingestion and analysis from a request payload."""
    appid = payload.get("appid")
    steam_payload = payload.get("steam_payload")
    game_metadata_payload = payload.get("game_metadata_payload")

    if not isinstance(appid, int):
        raise ValueError("appid must be provided as an integer.")

    fetched_from_steam = False
    if steam_payload is None:
        steam_payload = fetch_steam_reviews(appid)
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

    raw_reviews = normalize_steam_reviews(appid, steam_payload)
    result, processed_reviews = run_and_persist_analysis(
        raw_reviews,
        appid=appid,
        data_root=data_root,
    )

    FileStore(data_root).write_game_metadata(appid, game_metadata.to_dict())

    return {
        "appid": appid,
        "raw_review_count": len(raw_reviews),
        "processed_review_count": len(processed_reviews),
        "included_review_count": sum(
            1 for review in processed_reviews if review.included_in_analysis
        ),
        "sample_size_tier": result.sample_size_tier,
        "trend_status": result.trend_status,
        "metadata_collected": game_metadata.release_stage != "unknown" or bool(game_metadata.genres),
        "price_model": game_metadata.price_model,
        "release_stage": game_metadata.release_stage,
    }


def load_analysis_result(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Load a stored analysis result for one game."""
    store = FileStore(data_root)
    return store.read_json(Path("analysis") / f"{appid}.json")


def load_raw_reviews(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> list[dict[str, Any]]:
    """Load stored raw review records for one game."""
    store = FileStore(data_root)
    return store.read_json(Path("raw") / f"{appid}.json")


def load_processed_reviews(
    appid: int,
    data_root: str | Path = DEFAULT_DATA_ROOT,
) -> list[dict[str, Any]]:
    """Load stored processed review records for one game."""
    store = FileStore(data_root)
    return store.read_json(Path("processed") / f"{appid}.json")


def load_game_metadata(appid: int, data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Load stored game metadata for one game."""
    store = FileStore(data_root)
    return store.read_json(Path("metadata") / f"{appid}.json")


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
