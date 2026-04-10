"""Local JSON storage helpers for the review-insights MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileStore:
    """Persist structured data into the local app data directory."""

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

    def ensure_dir(self, relative_dir: str | Path) -> Path:
        target_dir = self.root_dir / Path(relative_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def write_json(self, relative_path: str | Path, payload: Any) -> Path:
        target_path = self.root_dir / Path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target_path

    def read_json(self, relative_path: str | Path) -> Any:
        target_path = self.root_dir / Path(relative_path)
        return json.loads(target_path.read_text(encoding="utf-8"))

    def write_raw_reviews(self, appid: int, payload: Any) -> Path:
        return self.write_json(Path("raw") / f"{appid}.json", payload)

    def write_game_metadata(self, appid: int, payload: Any) -> Path:
        return self.write_json(Path("metadata") / f"{appid}.json", payload)

    def write_processed_reviews(self, appid: int, payload: Any) -> Path:
        return self.write_json(Path("processed") / f"{appid}.json", payload)

    def write_analysis_result(self, appid: int, payload: Any) -> Path:
        return self.write_json(Path("analysis") / f"{appid}.json", payload)
