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
            """Serve the internal dashboard."""
            return FileResponse(FRONTEND_DIR / "index.html")

        @app.get("/app.js")
        def frontend_js():
            """Serve the dashboard script."""
            return FileResponse(FRONTEND_DIR / "app.js", media_type="text/javascript")

        @app.get("/styles.css")
        def frontend_css():
            """Serve the dashboard stylesheet."""
            return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")

    return app


app = create_app() if FastAPI is not None else None
