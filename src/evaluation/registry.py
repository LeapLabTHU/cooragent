from __future__ import annotations

from typing import Dict, List, Type

from .benchmarks.base import BaseBenchmark
from ..interface.evaluation import BenchmarkInfo


class BenchmarkRegistry:
    """Registry for all available benchmarks."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseBenchmark]] = {}

    def register_benchmark(self, name: str, benchmark_cls: Type[BaseBenchmark]) -> None:
        key = name.lower()
        self._registry[key] = benchmark_cls

    def get_benchmark(self, name: str) -> BaseBenchmark:
        key = name.lower()
        if key not in self._registry:
            raise KeyError(f"Benchmark not found: {name}")
        return self._registry[key]()

    def list_benchmarks(self) -> List[BenchmarkInfo]:
        infos: List[BenchmarkInfo] = []
        for cls in self._registry.values():
            try:
                inst = cls()
                infos.append(BenchmarkInfo(name=getattr(inst, "name", cls.__name__), version=getattr(inst, "version", "1.0")))
            except Exception:
                infos.append(BenchmarkInfo(name=cls.__name__, version="1.0"))
        return infos 