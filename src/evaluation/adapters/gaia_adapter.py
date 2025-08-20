from __future__ import annotations

from typing import Dict, List

from ..dataset import Task


class GAIATaskAdapter:
    def to_messages(self, task: Task) -> List[Dict[str, str]]:
        # Convert GAIA task to Cooragent messages format
        # Simplest form: single user message
        prompt = task.question
        return [{"role": "user", "content": prompt}]

    def parse_answer(self, response: Dict) -> str | None:
        # Placeholder: expect response dict to contain final text under 'answer' or 'content'
        return response.get("answer") or response.get("content") 