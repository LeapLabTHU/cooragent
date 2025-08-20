from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


class ResultStore:
    def __init__(self, base_dir: str = "./store/evaluation") -> None:
        self.base = Path(base_dir)
        self.results_dir = self.base / "results"
        self.reports_dir = self.base / "reports"
        self.transcripts_dir = self.base / "transcripts"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, name: str, data: Dict[str, Any]) -> str:
        path = self.results_dir / f"{name}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)

    def save_text(self, name: str, text: str) -> str:
        path = self.transcripts_dir / f"{name}.txt"
        with path.open("w", encoding="utf-8") as f:
            f.write(text)
        return str(path)

    def save_task_transcript(self, run_id: str, task_id: str, data: Dict[str, Any]) -> str:
        run_dir = self.transcripts_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{task_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path) 