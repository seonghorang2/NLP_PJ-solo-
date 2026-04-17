"""Application entrypoint for the review-insights backend."""

from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
except ImportError:  # pragma: no cover - exercised only when FastAPI is missing.
    FastAPI = None
    FileResponse = None

from api.routes import router

APP_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = APP_ROOT / "frontend"
MOCK_DATA_DIR = APP_ROOT / "data" / "mock"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def create_app():
    """Create the backend application instance."""
    if FastAPI is None:
        raise RuntimeError("fastapi is required to run the backend application.")

    app = FastAPI(title="review-insights")

    if router is not None:
        app.include_router(router)

    if FileResponse is not None:

        @app.get("/")
        def index():
            """Serve the consumer-facing report page."""
            return FileResponse(FRONTEND_DIR / "index.html", headers=NO_CACHE_HEADERS)

        @app.get("/app.js")
        def frontend_js():
            """Serve the frontend script."""
            return FileResponse(
                FRONTEND_DIR / "app.js",
                media_type="text/javascript",
                headers=NO_CACHE_HEADERS,
            )

        @app.get("/styles.css")
        def frontend_css():
            """Serve the report stylesheet."""
            return FileResponse(
                FRONTEND_DIR / "styles.css",
                media_type="text/css",
                headers=NO_CACHE_HEADERS,
            )

        @app.get("/howworks")
        def howworks_page():
            """Serve the presentation-only pipeline walkthrough page."""
            return FileResponse(FRONTEND_DIR / "howworks.html", headers=NO_CACHE_HEADERS)

        @app.get("/howworks.js")
        def howworks_js():
            """Serve the presentation-only pipeline walkthrough script."""
            return FileResponse(
                FRONTEND_DIR / "howworks.js",
                media_type="text/javascript",
                headers=NO_CACHE_HEADERS,
            )

        @app.get("/howworks.css")
        def howworks_css():
            """Serve the presentation-only pipeline walkthrough stylesheet."""
            return FileResponse(
                FRONTEND_DIR / "howworks.css",
                media_type="text/css",
                headers=NO_CACHE_HEADERS,
            )

        @app.get("/mock/howworks_pipeline.json")
        def howworks_mock_data():
            """Serve mock pipeline data for the presentation page."""
            return FileResponse(
                MOCK_DATA_DIR / "howworks_pipeline.json",
                media_type="application/json",
                headers=NO_CACHE_HEADERS,
            )

    return app


app = create_app() if FastAPI is not None else None
