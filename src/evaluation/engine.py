from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List
import logging

from .benchmarks.base import BaseBenchmark
from .dataset import Task
from ..interface.evaluation import (
    BenchmarkMetrics,
    EvaluationConfig,
    EvaluationResult,
    EvaluationScore,
    ExecutionConfig,
    TaskResult,
)
from .storage import ResultStore

logger = logging.getLogger(__name__)


class EvaluationEngine:
    async def execute_benchmark(self, benchmark: BaseBenchmark, config: EvaluationConfig) -> EvaluationResult:
        started_at = datetime.utcnow()
        bench_name = getattr(benchmark, "name", benchmark.__class__.__name__)
        logger.info(
            "Starting evaluation: benchmark=%s, subset=%s, limit=%s, max_concurrent=%s, timeout=%ss, mode=%s",
            bench_name,
            getattr(benchmark, "subset", None),
            config.limit,
            config.max_concurrent_tasks,
            config.timeout_per_task,
            config.execution_mode,
        )
        dataset = await benchmark.load_dataset()
        logger.info("Loaded dataset with %d tasks", len(dataset.tasks))

        # Subset limiting
        tasks = dataset.tasks[: config.limit] if config.limit else dataset.tasks
        logger.info("Evaluating %d tasks", len(tasks))

        # Execute tasks with simple concurrency control
        semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        scores: List[EvaluationScore] = []
        store = ResultStore(config.output_dir)

        def _truncate(text: str, max_len: int = 160) -> str:
            if text is None:
                return ""
            return text if len(text) <= max_len else text[:max_len] + "..."

        async def _execute_with_timeout(task: Task):
            from .adapters.workflow_adapter import WorkflowAdapter
            adapter = WorkflowAdapter()
            logger.debug("[Task %s] Invoking WorkflowAdapter in mode=%s", task.task_id, config.execution_mode)
            return await adapter.execute_as_workflow(
                task,
                mode=config.execution_mode,
                collect_transcript=config.debug_eval or config.save_details,
            )

        async def _run_task(task: Task) -> None:
            async with semaphore:
                logger.info("[Task %s] Start. Question: %s", task.task_id, _truncate(task.question))
                attempts = 0
                response = None
                pretty_lines: List[str] = []
                if config.debug_eval and config.pretty_console:
                    pretty_lines.append(f"\n=== Task {task.task_id} ===")
                    pretty_lines.append(f"Question: {task.question}")
                while True:
                    try:
                        if config.timeout_per_task and config.timeout_per_task > 0:
                            response = await asyncio.wait_for(
                                _execute_with_timeout(task), timeout=config.timeout_per_task
                            )
                        else:
                            response = await _execute_with_timeout(task)
                        logger.info("[Task %s] Completed execution", task.task_id)
                        # Pretty print final answer
                        if config.debug_eval and config.pretty_console:
                            answer_text = (response or {}).get("answer")
                            raw_output = (response or {}).get("raw_output")
                            pretty_lines.append(f"Final Answer: {answer_text}")
                            if raw_output and isinstance(raw_output, str):
                                pretty_lines.append("--- Raw Assistant Output (truncated) ---")
                                pretty_lines.append(_truncate(raw_output, 1200))
                            # If transcript exists, summarize agents/tools from events
                            transcript = (response or {}).get("transcript")
                            if isinstance(transcript, list):
                                agent_events = [e for e in transcript if e.get("event") in {"start_of_agent", "end_of_agent"}]
                                if agent_events:
                                    pretty_lines.append("--- Agent Execution ---")
                                    for e in agent_events:
                                        if e.get("event") == "start_of_agent":
                                            pretty_lines.append(f"-> Agent start: {e.get('data', {}).get('agent_name')}")
                                        elif e.get("event") == "end_of_agent":
                                            pretty_lines.append(f"<- Agent end: {e.get('data', {}).get('agent_name')}")
                                tool_events = [e for e in transcript if e.get("event") == "tool_event"]
                                if tool_events:
                                    pretty_lines.append("--- Tool Calls ---")
                                    for e in tool_events[:20]:
                                        d = e.get("data", {})
                                        typ = d.get("type")
                                        name = d.get("name")
                                        ts = d.get("timestamp")
                                        succ = d.get("success")
                                        if typ == "tool_start":
                                            pretty_lines.append(f"[start] {name} at {ts}")
                                        elif typ == "tool_end":
                                            pretty_lines.append(f"[end]   {name} at {ts} success={succ}")
                        break
                    except Exception as e:
                        attempts += 1
                        will_retry = config.retry_failed_tasks and attempts <= config.max_retries
                        logger.warning(
                            "[Task %s] Attempt %d failed: %s%s",
                            task.task_id,
                            attempts,
                            str(e),
                            "; retrying" if will_retry else "; no more retries",
                        )
                        if not config.retry_failed_tasks or attempts > config.max_retries:
                            response = {"answer": None, "error": str(e)}
                            break
                        await asyncio.sleep(0.1)
                score = await benchmark.evaluate_response(task, response)
                resp_text = (response or {}).get("answer")
                resp_len = len(resp_text) if isinstance(resp_text, str) else 0
                logger.info(
                    "[Task %s] Scored. RespLen=%d, Accuracy=%.3f, Completeness=%.3f, Efficiency=%.3f, Tool=%.3f",
                    task.task_id,
                    resp_len,
                    score.accuracy,
                    score.completeness,
                    score.efficiency,
                    score.tool_usage,
                )
                # Save detailed transcript if requested
                if config.save_details:
                    try:
                        store.save_task_transcript(
                            run_id=f"{benchmark.__class__.__name__}-{int(started_at.timestamp())}",
                            task_id=task.task_id,
                            data={
                                "task_id": task.task_id,
                                "question": task.question,
                                "response": response,
                                "score": score.model_dump(),
                            },
                        )
                    except Exception as se:
                        logger.warning("[Task %s] Failed saving transcript: %s", task.task_id, se)
                # Print pretty console output at end of task
                if pretty_lines:
                    try:
                        print("\n".join(pretty_lines))
                    except Exception:
                        pass
                scores.append(score)

        await asyncio.gather(*[_run_task(t) for t in tasks])

        metrics: BenchmarkMetrics = benchmark.calculate_metrics(scores)
        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        logger.info(
            "Evaluation done. num_tasks=%d, aggregate=%.3f, duration_ms=%d",
            len(tasks),
            metrics.aggregate_score,
            duration_ms,
        )

        return EvaluationResult(
            run_id=f"{benchmark.__class__.__name__}-{int(started_at.timestamp())}",
            benchmark=getattr(benchmark, "name", benchmark.__class__.__name__),
            version=getattr(benchmark, "version", "1.0"),
            config=config,
            metrics=metrics,
            scores=scores,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            num_tasks=len(tasks),
        )

    async def execute_task(self, task: Task, config: ExecutionConfig) -> TaskResult:
        started = datetime.utcnow()
        # Placeholder execution logic
        response = {"answer": None}
        finished = datetime.utcnow()
        return TaskResult(
            task_id=task.task_id,
            input={"question": task.question},
            response=response,
            start_time=started,
            end_time=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
        ) 