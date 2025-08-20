from __future__ import annotations

from typing import List
from ..interface.evaluation import EvaluationScore, BenchmarkMetrics


def average_metrics(scores: List[EvaluationScore]) -> BenchmarkMetrics:
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