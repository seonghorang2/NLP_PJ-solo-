"""Application entrypoint for the review-insights backend."""

from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover - exercised only when FastAPI is missing.
    FastAPI = None
    FileResponse = None
    HTMLResponse = None
    StaticFiles = None

from api.routes import router

APP_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = APP_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_DIST_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
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
        if StaticFiles is not None and FRONTEND_DIST_ASSETS_DIR.exists():
            app.mount(
                "/assets",
                StaticFiles(directory=FRONTEND_DIST_ASSETS_DIR),
                name="frontend-assets",
            )

        @app.get("/")
        def index():
            """Serve the consumer-facing report page."""
            dist_index_path = FRONTEND_DIST_DIR / "index.html"
            if dist_index_path.exists():
                return FileResponse(dist_index_path, headers=NO_CACHE_HEADERS)

            message = (
                "Frontend build not found. Run `npm install` and `npm run build` in "
                "`apps/review-insights/frontend`, then restart the server."
            )
            if HTMLResponse is not None:
                return HTMLResponse(content=message, status_code=503, headers=NO_CACHE_HEADERS)
            return {"detail": message}

    return app


app = create_app() if FastAPI is not None else None
