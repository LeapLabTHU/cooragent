from __future__ import annotations

from typing import Any, Dict
import logging
import json
import re

from ..dataset import Task

logger = logging.getLogger(__name__)


class WorkflowAdapter:
    def __init__(self) -> None:
        pass

    def _extract_final_answer(self, text: str | None) -> str | None:
        if not text:
            return None
        # Prefer explicit markers like "Final Answer: ..."
        patterns = [
            r"final\s*answer\s*[:\-]\s*(.+)",
            r"answer\s*[:\-]\s*(.+)",
            r"result\s*[:\-]\s*(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                # Clean up trailing punctuation/extra lines
                candidate = candidate.splitlines()[0].strip()
                candidate = candidate.rstrip(". ")
                return candidate
        # Fallback: return last numeric-looking token if present
        nums = re.findall(r"-?\d+(?:\.\d+)?", text)
        return nums[-1] if nums else text.strip()

    async def execute_as_workflow(self, task: Task, mode: str = "production", collect_transcript: bool = False) -> Dict[str, Any]:
        from src.interface.agent import AgentRequest, AgentMessage, TaskType, WorkMode, Lang
        from src.service.server import Server
        from .gaia_adapter import GAIATaskAdapter
        from src.tools.websocket_manager import websocket_manager

        server = Server()

        # Build primary user content
        content = (task.question or "").strip()
        extra_lines: list[str] = []

        # If GAIA provides attachments or auxiliary inputs, mention them succinctly
        attachments = (task.context or {}).get("attachments") if task.context else None
        if attachments:
            try:
                # Only include keys to avoid leaking dataset internals/answers
                att_summary = {k: (len(v) if isinstance(v, list) else "present") for k, v in attachments.items()}
            except Exception:
                att_summary = {"attachments": "present"}
            extra_lines.append(f"Attachments summary: {json.dumps(att_summary, ensure_ascii=False)}")

        # Fallback if question is empty
        if not content:
            adapter = GAIATaskAdapter()
            try:
                msgs = adapter.to_messages(task)
                if msgs and isinstance(msgs[0].get("content"), str) and msgs[0]["content"].strip():
                    content = msgs[0]["content"].strip()
            except Exception:
                pass

        if not content:
            # Last-resort fallback using safe metadata
            safe_meta = {}
            if task.metadata:
                for k, v in task.metadata.items():
                    if k.lower() not in {"answer", "expected_answer"}:
                        safe_meta[k] = v
            extra_lines.insert(0, f"GAIA Task ID: {task.task_id}")
            if safe_meta:
                try:
                    extra_lines.append(f"Context: {json.dumps(safe_meta, ensure_ascii=False)[:400]}")
                except Exception:
                    pass
            content = "Please solve the following GAIA task. Use tools if needed."

        if extra_lines:
            content = content + "\n\n" + "\n".join(extra_lines)

        messages = [AgentMessage(role="user", content=content)]
        request = AgentRequest(
            user_id="eval",
            lang=Lang.EN,
            task_type=TaskType.AGENT_WORKFLOW,
            messages=messages,
            debug=False,
            deep_thinking_mode=True,
            search_before_planning=False,
            coor_agents=[],
            workmode=WorkMode(mode) if isinstance(mode, str) else mode,
            workflow_id=None,
        )

        logger.info("[Task %s] Workflow start (mode=%s)", task.task_id, mode)
        chunks: list[str] = []
        transcript_events: list[Dict[str, Any]] = []
        async for event in server._run_agent_workflow(request):
            if collect_transcript:
                # Keep a clean minimal transcript copy
                event_copy = {k: v for k, v in event.items()}
                transcript_events.append(event_copy)
            if event.get("event") == "messages":
                data = event.get("data", {})
                delta = data.get("delta", {})
                content = delta.get("content")
                if content:
                    chunks.append(content)

        final_content = "".join(chunks) if chunks else None
        answer = self._extract_final_answer(final_content)
        logger.info(
            "[Task %s] Workflow end. chunks=%d, total_len=%d",
            task.task_id,
            len(chunks),
            len(final_content) if final_content else 0,
        )

        result: Dict[str, Any] = {"answer": answer or final_content}
        if collect_transcript:
            # Merge tool broadcast events from websocket_manager buffer
            tool_events = websocket_manager.get_and_clear_debug_events("eval")
            if tool_events:
                transcript_events.extend([{"event": "tool_event", "data": ev} for ev in tool_events])
            result["transcript"] = transcript_events
            result["raw_output"] = final_content
        return result 