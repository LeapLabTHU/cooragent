from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from ..dataset import Dataset, Task
from ...interface.evaluation import EvaluationScore, BenchmarkMetrics


class BaseBenchmark(ABC):
    name: str
    version: str
    subset: Optional[str] = None

    @abstractmethod
    async def load_dataset(self) -> Dataset:
        raise NotImplementedError

    @abstractmethod
    async def evaluate_response(self, task: Task, response: Any) -> EvaluationScore:
        raise NotImplementedError

    @abstractmethod
    def calculate_metrics(self, scores: List[EvaluationScore]) -> BenchmarkMetrics:
        raise NotImplementedError 