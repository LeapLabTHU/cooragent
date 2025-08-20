from __future__ import annotations

from typing import Dict, List

from .registry import BenchmarkRegistry
from .engine import EvaluationEngine
from ..interface.evaluation import EvaluationConfig, EvaluationResult, ScheduleConfig
from .storage import ResultStore


class EvaluationManager:
    def __init__(self) -> None:
        self.registry = BenchmarkRegistry()
        self.engine = EvaluationEngine()
        self._register_benchmarks()

    def _register_benchmarks(self) -> None:
        # Lazy import to avoid hard dependency at import time
        try:
            from .benchmarks.gaia.gaia_benchmark import GAIABenchmark

            self.registry.register_benchmark("gaia", GAIABenchmark)
        except Exception:
            # GAIA benchmark may not be available yet; ignore at init
            pass

    async def run_evaluation(self, benchmark_name: str, config: EvaluationConfig, **kwargs) -> EvaluationResult:
        benchmark = self.registry.get_benchmark(benchmark_name)
        # Pass subset from config to benchmark instance if it needs it
        if hasattr(benchmark, "subset"):
            benchmark.subset = config.subset
        result = await self.engine.execute_benchmark(benchmark, config)
        # Persist run-level summary and config
        try:
            store = ResultStore(config.output_dir)
            store.save_json(
                name=result.run_id,
                data={
                    "run_id": result.run_id,
                    "benchmark": result.benchmark,
                    "metrics": result.metrics.model_dump(),
                    "config": result.config.model_dump(),
                    "num_tasks": result.num_tasks,
                    "duration_ms": result.duration_ms,
                },
            )
        except Exception:
            # Non-fatal
            pass
        return result

    async def schedule_evaluation(self, schedule_config: ScheduleConfig) -> None:
        # Placeholder for future scheduling support
        return None

    def get_evaluation_history(self, filters: Dict) -> List[EvaluationResult]:
        # Placeholder for future persistence
        return [] 