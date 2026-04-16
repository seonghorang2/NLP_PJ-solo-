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

    return app


app = create_app() if FastAPI is not None else None
