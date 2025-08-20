from __future__ import annotations

from typing import List

from ..interface.evaluation import EvaluationResult


class ReportGenerator:
    def generate_markdown_report(self, result: EvaluationResult) -> str:
        # Minimal report content
        lines: List[str] = []
        lines.append(f"# Evaluation Report - {result.benchmark}")
        lines.append("")
        lines.append(f"Run ID: {result.run_id}")
        lines.append(f"Tasks: {result.num_tasks}")
        lines.append(f"Score: {result.metrics.aggregate_score:.3f}")
        return "\n".join(lines) 