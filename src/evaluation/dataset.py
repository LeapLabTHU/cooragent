from __future__ import annotations

from typing import Any, Dict, List, Optional


class Task:
    def __init__(self, task_id: str, question: str, expected_output: Any, context: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None, evaluation_criteria: Optional[Dict[str, Any]] = None) -> None:
        self.task_id = task_id
        self.question = question
        self.expected_output = expected_output
        self.context = context or {}
        self.metadata = metadata or {}
        self.evaluation_criteria = evaluation_criteria or {}


class Dataset:
    def __init__(self, tasks: List[Task]) -> None:
        self.tasks = tasks
        self.metadata: Dict[str, Any] = {}

    def filter(self, criteria: Dict[str, Any]) -> "Dataset":
        # TODO: implement real filtering
        return self

    def split(self, ratios: List[float]) -> List["Dataset"]:
        # TODO: implement splitting by ratios
        return [self] 