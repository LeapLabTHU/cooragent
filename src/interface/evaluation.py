from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EvaluationConfig(BaseModel):
    benchmark: str = Field(default="gaia")
    subset: Optional[str] = Field(default=None)
    limit: Optional[int] = Field(default=None)
    max_concurrent_tasks: int = Field(default=5)
    timeout_per_task: int = Field(default=300)
    retry_failed_tasks: bool = Field(default=True)
    max_retries: int = Field(default=1)
    execution_mode: str = Field(default="launch")
    use_cache: bool = Field(default=True)
    capture_reasoning: bool = Field(default=True)
    capture_tool_usage: bool = Field(default=True)
    output_dir: str = Field(default="./store/evaluation")
    extra: Dict[str, Any] = Field(default_factory=dict)
    debug_eval: bool = Field(default=False)
    pretty_console: bool = Field(default=True)
    save_details: bool = Field(default=True)


class ScheduleConfig(BaseModel):
    cron: str
    active: bool = True


class EvaluationScore(BaseModel):
    task_id: str
    accuracy: float = 0.0
    completeness: float = 0.0
    efficiency: float = 0.0
    tool_usage: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkMetrics(BaseModel):
    accuracy: float = 0.0
    completeness: float = 0.0
    efficiency: float = 0.0
    tool_usage: float = 0.0
    aggregate_score: float = 0.0
    totals: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    task_id: str
    input: Dict[str, Any]
    response: Any
    start_time: datetime
    end_time: datetime
    duration_ms: int
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_trace: Optional[str] = None


class ExecutionConfig(BaseModel):
    timeout_seconds: int = 300
    record_tool_calls: bool = True
    record_reasoning: bool = True


class EvaluationResult(BaseModel):
    run_id: str
    benchmark: str
    version: str = "1.0"
    config: EvaluationConfig
    metrics: BenchmarkMetrics
    scores: List[EvaluationScore]
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    num_tasks: int
    notes: Optional[str] = None


class BenchmarkInfo(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) 