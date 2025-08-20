from __future__ import annotations

from typing import Any, List

from ..base import BaseBenchmark
from ...dataset import Dataset, Task
from ....interface.evaluation import EvaluationScore, BenchmarkMetrics


class GAIABenchmark(BaseBenchmark):
    def __init__(self) -> None:
        self.name = "GAIA"
        self.version = "1.0"
        self.subset = "2023_level1"  # Default subset

    async def load_dataset(self) -> Dataset:
        from .gaia_loader import GAIADatasetLoader
        DEFAULT_CONFIG = "2023_level1"
        if self.subset and (
            self.subset in {"train", "validation", "test"} or ":" in self.subset or "[" in self.subset or "]" in self.subset
        ):
            # Treat as split expression
            loader = GAIADatasetLoader(subset=self.subset, config_name=DEFAULT_CONFIG)
        else:
            config_name = self.subset or DEFAULT_CONFIG
            loader = GAIADatasetLoader(config_name=config_name)
        return await loader.load_from_huggingface()

    async def evaluate_response(self, task: Task, response: Any) -> EvaluationScore:
        # Naive scoring: if expected answer exists and is substring of response, mark as accurate
        text = (response or {}).get("answer") or ""
        expected = (task.expected_output or "")
        accuracy = 1.0 if expected and str(expected).strip().lower() in str(text).strip().lower() else 0.0
        return EvaluationScore(task_id=task.task_id, accuracy=accuracy, passed=accuracy >= 0.5)

    def calculate_metrics(self, scores: List[EvaluationScore]) -> BenchmarkMetrics:
        # Simple average calculation placeholder
        if not scores:
            return BenchmarkMetrics()
        n = len(scores)
        acc = sum(s.accuracy for s in scores) / n
        comp = sum(s.completeness for s in scores) / n
        eff = sum(s.efficiency for s in scores) / n
        tool = sum(s.tool_usage for s in scores) / n
        return BenchmarkMetrics(
            accuracy=acc,
            completeness=comp,
            efficiency=eff,
            tool_usage=tool,
            aggregate_score=(acc + comp + eff + tool) / 4.0,
            totals={"num_tasks": n},
        ) 