"""Offline SDK and AgentManager dispatch through a local synthetic MCP server.

The unrelated built-in tools and the LLM are synthetic. MCP transport, tool
discovery, AgentManager registration, LangGraph scheduling, and MCP tool call
use the real pinned dependencies.
"""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests" / "fixtures" / "synthetic_mcp_server.py"


class SyntheticToolCallingModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "synthetic-tool-calling-model"

    def bind_tools(self, tools, **kwargs):
        assert any(tool.name == "echo" for tool in tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tool_messages = [
            message for message in messages if isinstance(message, ToolMessage)
        ]
        if tool_messages:
            assert "synthetic:from-agent" in str(tool_messages[-1].content)
            answer = AIMessage(content="synthetic model finished")
        else:
            answer = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo",
                        "args": {"value": "from-agent"},
                        "id": "synthetic-1",
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=answer)])


@pytest.fixture(params=["streamable_http", "sse"])
def synthetic_http_server(monkeypatch, request):
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]

    token = "synthetic-host-token"
    env = {**os.environ, "SYNTHETIC_EXPECTED_TOKEN": token}
    process = subprocess.Popen(
        [sys.executable, str(SERVER), str(port), request.param],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail(f"Synthetic server exited: {process.stderr.read()}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("Synthetic server did not start")
        monkeypatch.setenv("SYNTHETIC_CLIENT_TOKEN", token)
        path = "mcp" if request.param == "streamable_http" else "sse"
        yield {"url": f"http://127.0.0.1:{port}/{path}", "transport": request.param}
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def _load_source(name, path, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _real_agent_manager_with_stubbed_unrelated_tools(monkeypatch, config_path):
    """Import the real manager while avoiding browser/search tool startup."""
    monkeypatch.setenv("USE_MCP_TOOLS", "False")
    fake_tools = ModuleType("src.tools")
    for name in (
        "bash_tool",
        "browser_tool",
        "crawl_tool",
        "python_repl_tool",
        "tavily_tool",
    ):
        setattr(
            fake_tools,
            name,
            SimpleNamespace(name=name, description=f"synthetic {name}"),
        )
    monkeypatch.setitem(sys.modules, "src.tools", fake_tools)

    package = ModuleType("src.manager")
    package.__path__ = [str(ROOT / "src" / "manager")]
    monkeypatch.setitem(sys.modules, "src.manager", package)
    config_module = _load_source(
        "src.manager.mcp", ROOT / "src" / "manager" / "mcp.py", monkeypatch
    )
    monkeypatch.setattr(config_module, "CONFIG_FILE_PATH", str(config_path))
    agents_module = _load_source(
        "src.manager.agents", ROOT / "src" / "manager" / "agents.py", monkeypatch
    )
    return agents_module, config_module


def _cooragent_dispatch_node(monkeypatch, manager):
    """Load the repository's real proxy node with unrelated LLM/cache stubbed."""
    llm_module = ModuleType("src.llm.llm")
    llm_module.get_llm_by_type = lambda _kind: SyntheticToolCallingModel()
    monkeypatch.setitem(sys.modules, "src.llm.llm", llm_module)

    search_module = ModuleType("src.tools.search")
    search_module.tavily_tool = SimpleNamespace(
        name="tavily_tool", description="synthetic"
    )
    monkeypatch.setitem(sys.modules, "src.tools.search", search_module)

    workflow_package = ModuleType("src.workflow")
    workflow_package.__path__ = [str(ROOT / "src" / "workflow")]
    monkeypatch.setitem(sys.modules, "src.workflow", workflow_package)
    cache_module = ModuleType("src.workflow.cache")
    cache_module.workflow_cache = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "src.workflow.cache", cache_module)

    sys.modules["src.manager"].agent_manager = manager
    _load_source(
        "src.workflow.graph", ROOT / "src" / "workflow" / "graph.py", monkeypatch
    )
    return _load_source(
        "src.workflow.coor_task",
        ROOT / "src" / "workflow" / "coor_task.py",
        monkeypatch,
    )


def test_pinned_sdk_manager_and_langgraph_dispatch(
    synthetic_http_server, monkeypatch, tmp_path
):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "synthetic": {
                        "url": synthetic_http_server["url"],
                        "transport": synthetic_http_server["transport"],
                        "bearerTokenEnv": "SYNTHETIC_CLIENT_TOKEN",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    # The repository initializes its module-global manager with asyncio.run()
    # at import time, so load it before starting the test event loop.
    agents_module, config_module = _real_agent_manager_with_stubbed_unrelated_tools(
        monkeypatch, config_path
    )

    async def run():
        connections = config_module.mcp_client_config()
        assert connections["synthetic"]["url"] == synthetic_http_server["url"]
        assert (
            connections["synthetic"]["headers"]["Authorization"]
            == "Bearer synthetic-host-token"
        )

        # The adapter itself performs transport discovery and tool invocation.
        sdk_tools = await MultiServerMCPClient(connections).get_tools()
        assert {tool.name for tool in sdk_tools} == {"echo", "child_env"}
        sdk_echo = next(tool for tool in sdk_tools if tool.name == "echo")
        assert "synthetic:from-sdk" in str(
            await sdk_echo.ainvoke({"value": "from-sdk"})
        )

        # The repository's real AgentManager registers the same server tool.
        manager = agents_module.AgentManager(
            tmp_path / "tools", tmp_path / "agents", tmp_path / "prompts"
        )
        await manager.load_mcp_tools()
        assert "echo" in manager.available_tools
        assert "synthetic:from-manager" in str(
            await manager.available_tools["echo"].ainvoke({"value": "from-manager"})
        )

        # LangGraph schedules the registered tool. Only model decisions are fake.
        graph = create_react_agent(
            SyntheticToolCallingModel(), [manager.available_tools["echo"]]
        )
        result = await graph.ainvoke({"messages": [HumanMessage(content="Call echo")]})
        tool_results = [
            message
            for message in result["messages"]
            if isinstance(message, ToolMessage)
        ]
        assert len(tool_results) == 1
        assert "synthetic:from-agent" in str(tool_results[0].content)

        # The production proxy node also resolves this registered MCP tool and
        # dispatches it through LangGraph; only its model/cache peers are fake.
        from src.interface.agent import Agent
        from src.interface.mcp import Tool

        manager.available_agents["synthetic-agent"] = Agent(
            user_id="synthetic-user",
            agent_name="synthetic-agent",
            nick_name="synthetic-agent",
            description="offline fixture",
            llm_type="basic",
            selected_tools=[Tool(name="echo", description="synthetic echo")],
            prompt="Call the available echo tool.",
        )
        proxy = _cooragent_dispatch_node(monkeypatch, manager)
        command = await proxy.agent_proxy_node(
            {
                "workflow_mode": "polish",
                "next": "synthetic-agent",
                "user_id": "synthetic-user",
                "messages": [{"role": "user", "content": "Call echo"}],
            }
        )
        assert command.goto == "publisher"
        assert command.update["messages"][0]["content"] == "synthetic model finished"

    asyncio.run(run())


def test_pinned_stdio_child_environment_is_scoped(monkeypatch, tmp_path):
    monkeypatch.delenv("SYNTHETIC_CHILD_ONLY", raising=False)
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "local": {
                        "command": sys.executable,
                        "args": [str(SERVER)],
                        "env": {"SYNTHETIC_CHILD_ONLY": "synthetic-child-value"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    _agents_module, config_module = _real_agent_manager_with_stubbed_unrelated_tools(
        monkeypatch, config_path
    )

    async def run():
        tools = await MultiServerMCPClient(
            config_module.mcp_client_config()
        ).get_tools()
        child_tool = next(tool for tool in tools if tool.name == "child_env")
        assert "synthetic-child-value" in str(await child_tool.ainvoke({}))

    asyncio.run(run())
    assert "SYNTHETIC_CHILD_ONLY" not in os.environ


def test_synthetic_server_rejects_wrong_bearer_without_logging_it(
    synthetic_http_server, monkeypatch, tmp_path, caplog
):
    wrong_token = "wrong-synthetic-token"
    monkeypatch.setenv("SYNTHETIC_CLIENT_TOKEN", wrong_token)
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "synthetic": {
                        "url": synthetic_http_server["url"],
                        "transport": synthetic_http_server["transport"],
                        "bearerTokenEnv": "SYNTHETIC_CLIENT_TOKEN",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    _agents_module, config_module = _real_agent_manager_with_stubbed_unrelated_tools(
        monkeypatch, config_path
    )

    async def discover():
        await MultiServerMCPClient(config_module.mcp_client_config()).get_tools()

    with pytest.raises(Exception) as error:
        asyncio.run(discover())
    assert wrong_token not in caplog.text
    assert wrong_token not in str(error.value)
