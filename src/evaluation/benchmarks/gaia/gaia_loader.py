from __future__ import annotations

from typing import Any, Dict, List

import os
import logging

from datasets import load_dataset  # type: ignore

from ...dataset import Dataset, Task

logger = logging.getLogger(__name__)


class GAIADatasetLoader:
    def __init__(self, subset: str | None = None, limit: int | None = None, config_name: str | None = None) -> None:
        self.subset = subset or "validation[:10]"
        self.limit = limit
        self.config_name = config_name

    async def load_from_huggingface(self) -> Dataset:
        # Load a small split for smoke testing; users can configure subset
        dataset_path = "gaia-benchmark/GAIA"
        token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_TOKEN")
        load_kwargs: Dict[str, Any] = {"split": self.subset}
        if self.config_name:
            load_kwargs["name"] = self.config_name

        logger.info(
            "Loading dataset: path=%s, config_name=%s, split=%s, token_present=%s",
            dataset_path,
            self.config_name,
            self.subset,
            bool(token),
        )

        try:
            if token:
                # Prefer new API (token=...), fall back to legacy (use_auth_token=...)
                try:
                    hf = load_dataset(dataset_path, token=token, **load_kwargs)
                except TypeError:
                    hf = load_dataset(dataset_path, use_auth_token=token, **load_kwargs)  # type: ignore[call-arg]
            else:
                hf = load_dataset(dataset_path, **load_kwargs)
        except Exception as e:
            message = str(e)
            if "401" in message or "403" in message:
                raise RuntimeError(
                    (
                        "Access to 'gaia-benchmark/GAIA' was denied (HTTP 401/403). "
                        "Ensure you are logged in and have accepted the dataset's terms: "
                        "https://huggingface.co/datasets/gaia-benchmark/GAIA. "
                        "You can export an auth token via the environment variable 'HUGGINGFACE_HUB_TOKEN' or 'HF_TOKEN'."
                    )
                ) from e
            raise

        tasks: List[Task] = []
        for i, row in enumerate(hf):
            if self.limit is not None and i >= self.limit:
                break
            tasks.append(self.preprocess_task(row))
        logger.info("Dataset loaded. tasks=%d (limit=%s)", len(tasks), self.limit)
        return Dataset(tasks=tasks)

    def _extract_question_text(self, raw_task: Dict[str, Any]) -> str:
        """Best-effort extraction of the question text from GAIA row variants."""
        # Direct fields first
        candidates_in_order = [
            "question",
            "question_text",
            "question_en",
            "prompt",
            "instruction",
            "input",
            "query",
            "problem_statement",
            "problem",
            "text",
        ]
        for key in candidates_in_order:
            val = raw_task.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
            # Sometimes nested under a dict/list (e.g., problem: {text: ...})
            if isinstance(val, dict):
                inner_text = val.get("text") or val.get("question") or val.get("content")
                if isinstance(inner_text, str) and inner_text.strip():
                    return inner_text.strip()
            if isinstance(val, list):
                joined = "\n".join([str(x) for x in val if isinstance(x, str)])
                if joined.strip():
                    return joined.strip()

        # Heuristic: any key that contains these substrings
        needle_keys = ("question", "prompt", "instruction")
        for k, v in raw_task.items():
            if any(n in k.lower() for n in needle_keys) and isinstance(v, str) and v.strip():
                return v.strip()

        # Fallback to empty string
        return ""

    def _extract_attachments(self, raw_task: Dict[str, Any]) -> Dict[str, Any]:
        """Collect references to any attachments or auxiliary inputs if present."""
        attachments: Dict[str, Any] = {}
        for key in [
            "attachments",
            "files",
            "images",
            "image",
            "tables",
            "table",
            "urls",
            "url",
            "resources",
        ]:
            val = raw_task.get(key)
            if val:
                attachments[key] = val
        return attachments

    def preprocess_task(self, raw_task: Dict[str, Any]) -> Task:
        # GAIA rows typically include id, question, and answer/reference fields
        task_id = str(raw_task.get("id", raw_task.get("task_id", len(raw_task))))
        question = self._extract_question_text(raw_task)
        expected = raw_task.get("answer", raw_task.get("expected_answer", None))
        # Preserve other metadata
        metadata = {k: raw_task[k] for k in raw_task.keys() if k not in ("id", "task_id", "question", "answer", "expected_answer")}
        context: Dict[str, Any] = {}
        attachments = self._extract_attachments(raw_task)
        if attachments:
            context["attachments"] = attachments

        if not question:
            logger.warning("GAIA row %s has empty question. Available keys: %s", task_id, list(raw_task.keys()))

        return Task(task_id=task_id, question=question, expected_output=expected, context=context or None, metadata=metadata) 