"""
Decorator-based interface for MCP Agent applications.
Provides a simplified way to create and manage agents using decorators.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from functools import partial
from typing import (
    Any,
    Dict,
    Optional,
    TypeVar,
)

import yaml

# TODO -- reinstate once Windows&Python 3.13 platform issues are fixed
# import readline  # noqa: F401
from rich import print

from mcp_agent.app import MCPApp
from mcp_agent.config import Settings
from mcp_agent.core.agent_app import AgentApp
from mcp_agent.core.agent_types import AgentType
from mcp_agent.core.decorators import (
    _create_decorator,
    agent,
    chain,
    evaluator_optimizer,
    orchestrator,
    parallel,
    passthrough,
    router,
)
from mcp_agent.core.error_handling import handle_error
from mcp_agent.core.exceptions import (
    AgentConfigError,
    CircularDependencyError,
    ModelConfigError,
    PromptExitError,
    ProviderKeyError,
    ServerConfigError,
    ServerInitializationError,
)
from mcp_agent.core.factory import (
    create_agents_by_type,
    create_agents_in_dependency_order,
    create_basic_agents,
    get_model_factory,
)
from mcp_agent.core.proxies import LLMAgentProxy
from mcp_agent.core.types import ProxyDict
from mcp_agent.core.validation import (
    validate_server_references,
    validate_workflow_references,
)
from mcp_agent.mcp_server import AgentMCPServer

T = TypeVar("T")  # For the wrapper classes


class FastAgent:
    """
    A decorator-based interface for MCP Agent applications.
    Provides a simplified way to create and manage agents using decorators.
    """

    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        ignore_unknown_args: bool = False,
    ) -> None:
        """
        Initialize the decorator interface.

        Args:
            name: Name of the application
            config_path: Optional path to config file
        """
        # Initialize ContextDependent
        super().__init__()

        # Setup command line argument parsing
        parser = argparse.ArgumentParser(description="MCP Agent Application")
        parser.add_argument(
            "--model",
            help="Override the default model for all agents. Precedence is default < config_file < command line < constructor",
        )
        parser.add_argument(
            "--agent",
            help="Specify the agent to send a message to (used with --message)",
        )
        parser.add_argument(
            "-m",
            "--message",
            help="Message to send to the specified agent (requires --agent)",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Disable progress display, tool and message logging for cleaner output",
        )

        if ignore_unknown_args:
            known_args, _ = parser.parse_known_args()
            self.args = known_args
        else:
            self.args = parser.parse_args()

        # Quiet mode will be handled in _load_config()

        self.name = name
        self.config_path = config_path
        self._load_config()

        # Create the MCPApp with the config
        self.app = MCPApp(
            name=name,
            settings=Settings(**self.config) if hasattr(self, "config") else None,
        )
        self.agents: Dict[str, Dict[str, Any]] = {}

        # Bind decorator methods to this instance
        self._create_decorator = _create_decorator.__get__(self)
        self.agent = agent.__get__(self)
        self.orchestrator = orchestrator.__get__(self)
        self.parallel = parallel.__get__(self)
        self.evaluator_optimizer = evaluator_optimizer.__get__(self)
        self.router = router.__get__(self)
        self.chain = chain.__get__(self)
        self.passthrough = passthrough.__get__(self)

    # _create_proxy moved to factory.py

    @property
    def context(self):
        """Access the application context"""
        return self.app.context

    def _load_config(self) -> None:
        """Load configuration from YAML file, properly handling without dotenv processing"""
        if self.config_path:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f) or {}

    # Validation methods moved to validation.py

    def _get_model_factory(
        self,
        model: Optional[str] = None,
        request_params: Optional[Any] = None,
    ) -> Any:
        """
        Get model factory using specified or default model.
        Model string is parsed by ModelFactory to determine provider and reasoning effort.

        Args:
            model: Optional model specification string
            request_params: Optional RequestParams to configure LLM behavior

        Returns:
            ModelFactory instance for the specified or default model
        """
        # Wrap the factory function to use our context and CLI model
        return get_model_factory(
            self.context,
            model=model,
            request_params=request_params,
            cli_model=self.args.model if hasattr(self, "args") else None,
        )

    async def _create_agents_by_type(
        self,
        agent_app: MCPApp,
        agent_type: AgentType,
        active_agents: ProxyDict = None,
        **kwargs,
    ) -> ProxyDict:
        """
        Generic method to create agents of a specific type.

        Args:
            agent_app: The main application instance
            agent_type: Type of agents to create
            active_agents: Dictionary of already created agents/proxies (for dependencies)
            **kwargs: Additional type-specific parameters

        Returns:
            Dictionary of initialized agents wrapped in appropriate proxies
        """
        # Create a model factory function that we can pass to the factory module
        model_factory_func = partial(self._get_model_factory)

        return await create_agents_by_type(
            agent_app,
            self.agents,
            agent_type,
            active_agents,
            model_factory_func=model_factory_func,
            **kwargs,
        )

    async def _create_basic_agents(self, agent_app: MCPApp) -> ProxyDict:
        """
        Create and initialize basic agents with their configurations.

        Args:
            agent_app: The main application instance

        Returns:
            Dictionary of initialized basic agents wrapped in appropriate proxies
        """
        model_factory_func = partial(self._get_model_factory)
        return await create_basic_agents(agent_app, self.agents, model_factory_func)

    async def _create_orchestrators(self, agent_app: MCPApp, active_agents: ProxyDict) -> ProxyDict:
        """
        Create orchestrator agents.

        Args:
            agent_app: The main application instance
            active_agents: Dictionary of already created agents/proxies

        Returns:
            Dictionary of initialized orchestrator agents wrapped in appropriate proxies
        """
        return await self._create_agents_by_type(agent_app, AgentType.ORCHESTRATOR, active_agents)

    async def _create_evaluator_optimizers(self, agent_app: MCPApp, active_agents: ProxyDict) -> ProxyDict:
        """
        Create evaluator-optimizer workflows.

        Args:
            agent_app: The main application instance
            active_agents: Dictionary of already created agents/proxies

        Returns:
            Dictionary of initialized evaluator-optimizer workflows
        """
        return await self._create_agents_by_type(agent_app, AgentType.EVALUATOR_OPTIMIZER, active_agents)

    async def _create_parallel_agents(self, agent_app: MCPApp, active_agents: ProxyDict) -> ProxyDict:
        """
        Create parallel execution agents in dependency order.

        Args:
            agent_app: The main application instance
            active_agents: Dictionary of already created agents/proxies

        Returns:
            Dictionary of initialized parallel agents
        """
        model_factory_func = partial(self._get_model_factory)
        return await create_agents_in_dependency_order(
            agent_app,
            self.agents,
            active_agents,
            AgentType.PARALLEL,
            model_factory_func,
        )

    async def _create_agents_in_dependency_order(self, agent_app: MCPApp, active_agents: ProxyDict, agent_type: AgentType) -> ProxyDict:
        """
        Create agents in dependency order to avoid circular references.
        Works for both Parallel and Chain workflows.

        Args:
            agent_app: The main application instance
            active_agents: Dictionary of already created agents/proxies
            agent_type: Type of agents to create (AgentType.PARALLEL or AgentType.CHAIN)

        Returns:
            Dictionary of initialized agents
        """
        model_factory_func = partial(self._get_model_factory)
        return await create_agents_in_dependency_order(agent_app, self.agents, active_agents, agent_type, model_factory_func)

    async def _create_routers(self, agent_app: MCPApp, active_agents: ProxyDict) -> ProxyDict:
        """
        Create router agents.

        Args:
            agent_app: The main application instance
            active_agents: Dictionary of already created agents

        Returns:
            Dictionary of initialized router agents
        """
        return await self._create_agents_by_type(agent_app, AgentType.ROUTER, active_agents)

    @asynccontextmanager
    async def run(self):
        """
        Context manager for running the application.
        Performs validation and provides user-friendly error messages.
        """
        active_agents = {}
        had_error = False
        await self.app.initialize()

        # Handle quiet mode by disabling logger settings after initialization
        quiet_mode = hasattr(self, "args") and self.args.quiet

        try:
            async with self.app.run() as agent_app:
                # Apply quiet mode directly to the context's config if needed
                if quiet_mode and hasattr(agent_app.context, "config") and hasattr(agent_app.context.config, "logger"):
                    # Apply after initialization but before agents are created
                    agent_app.context.config.logger.progress_display = False
                    agent_app.context.config.logger.show_chat = False
                    agent_app.context.config.logger.show_tools = False

                    # Directly disable the progress display singleton
                    from mcp_agent.progress_display import progress_display

                    progress_display.stop()  # This will stop and hide the display

                # Pre-flight validation
                validate_server_references(self.context, self.agents)
                validate_workflow_references(self.agents)

                # Create all types of agents in dependency order
                # First create basic agents
                active_agents = await self._create_basic_agents(agent_app)

                # Create parallel agents next as they might be dependencies
                parallel_agents = await self._create_parallel_agents(agent_app, active_agents)
                active_agents.update(parallel_agents)

                # Create routers next
                routers = await self._create_routers(agent_app, active_agents)
                active_agents.update(routers)

                # Create chains next - MOVED UP because evaluator-optimizers might depend on chains
                chains = await self._create_agents_in_dependency_order(agent_app, active_agents, AgentType.CHAIN)
                active_agents.update(chains)

                # Now create evaluator-optimizers AFTER chains are available
                evaluator_optimizers = await self._create_evaluator_optimizers(agent_app, active_agents)
                active_agents.update(evaluator_optimizers)

                # Create orchestrators last as they might depend on any other agent type
                orchestrators = await self._create_orchestrators(agent_app, active_agents)

                # Add orchestrators to active_agents (other types were already added)
                active_agents.update(orchestrators)

                # Create wrapper with all agents
                wrapper = AgentApp(agent_app, active_agents)

                # Store reference to AgentApp in MCPApp for proxies to access
                agent_app._agent_app = wrapper

                # Handle direct message sending if --agent and --message are provided
                if self.args.agent and self.args.message:
                    # 将命令行处理移到单独的方法中，但仍然返回AgentApp对象
                    await self._handle_cli_message(wrapper)

                yield wrapper

        except ServerConfigError as e:
            had_error = True
            self._handle_error(
                e,
                "Server Configuration Error",
                "Please check your 'fastagent.config.yaml' configuration file and add the missing server definitions.",
            )
            raise SystemExit(1)

        except ProviderKeyError as e:
            had_error = True
            self._handle_error(
                e,
                "Provider Configuration Error",
                "Please check your 'fastagent.secrets.yaml' configuration file and ensure all required API keys are set.",
            )
            raise SystemExit(1)

        except AgentConfigError as e:
            had_error = True
            self._handle_error(
                e,
                "Workflow or Agent Configuration Error",
                "Please check your agent definition and ensure names and references are correct.",
            )
            raise SystemExit(1)

        except ServerInitializationError as e:
            had_error = True
            self._handle_error(
                e,
                "MCP Server Startup Error",
                "There was an error starting up the MCP Server.",
            )
            raise SystemExit(1)

        except ModelConfigError as e:
            had_error = True
            self._handle_error(
                e,
                "Model Configuration Error",
                "Common models: gpt-4o, o3-mini, sonnet, haiku. for o3, set reasoning effort with o3-mini.high",
            )
            raise SystemExit(1)

        except CircularDependencyError as e:
            had_error = True
            self._handle_error(
                e,
                "Circular Dependency Detected",
                "Check your agent configuration for circular dependencies.",
            )
            raise SystemExit(1)

        except PromptExitError as e:
            had_error = True
            self._handle_error(
                e,
                "User requested exit",
            )
            raise SystemExit(1)

        finally:
            # Clean up any active agents without re-raising errors
            if active_agents and not had_error:
                for name, proxy in active_agents.items():
                    if isinstance(proxy, LLMAgentProxy):
                        try:
                            await proxy._agent.__aexit__(None, None, None)
                        except Exception as e:
                            print(f"DEBUG {e.message}")
                            pass  # Ignore cleanup errors

    def _handle_error(self, e: Exception, error_type: str, suggestion: str = None) -> None:
        """
        Handle errors with consistent formatting and messaging.

        Args:
            e: The exception that was raised
            error_type: Type of error to display
            suggestion: Optional suggestion message to display
        """
        handle_error(e, error_type, suggestion)

    def _log_agent_load(self, agent_name: str) -> None:
        # This function is no longer needed - agent loading is now handled in factory.py
        pass

    def create_mcp_server(
        self,
        agent_app_instance: AgentApp,
        server_name: str = None,
        server_description: str = None,
    ) -> AgentMCPServer:
        """
        Create an MCP server that exposes the agents as tools.

        Args:
            agent_app_instance: The AgentApp instance with initialized agents
            server_name: Optional custom name for the MCP server
            server_description: Optional description for the MCP server

        Returns:
            An AgentMCPServer instance ready to be run
        """
        return AgentMCPServer(
            agent_app=agent_app_instance,
            server_name=server_name or f"{self.name}-MCP-Server",
            server_description=server_description,
        )

    async def run_with_mcp_server(
        self,
        transport: str = "sse",
        host: str = "0.0.0.0",
        port: int = 8000,
        server_name: str = None,
        server_description: str = None,
    ) -> None:
        """
        Run the FastAgent application and expose agents through an MCP server.

        Args:
            transport: Transport protocol to use ("stdio" or "sse")
            host: Host address for the server when using SSE
            port: Port for the server when using SSE
            server_name: Optional custom name for the MCP server
            server_description: Optional description for the MCP server
        """
        async with self.run() as agent_app:
            # Create the MCP server
            mcp_server = self.create_mcp_server(
                agent_app_instance=agent_app,
                server_name=server_name,
                server_description=server_description,
            )

            # Run the MCP server in a separate task
            server_task = asyncio.create_task(mcp_server.run_async(transport=transport, host=host, port=port))

            try:
                # Wait for the server task to complete (or be cancelled)
                await server_task
            except asyncio.CancelledError:
                # Propagate cancellation
                server_task.cancel()
                await asyncio.gather(server_task, return_exceptions=True)
                raise

    async def _handle_cli_message(self, agent_app):
        """
        处理命令行参数中的消息发送请求，但不影响上下文管理器的返回值。
        
        Args:
            agent_app: 已初始化的AgentApp实例
        """
        agent_name = self.args.agent
        message = self.args.message

        if agent_name not in agent_app:
            available_agents = ", ".join(agent_app.keys())
            print(f"\n\nError: Agent '{agent_name}' not found. Available agents: {available_agents}")
            raise SystemExit(1)

        try:
            # 获取响应
            response = await agent_app[agent_name].send(message)

            # 只在安静模式下打印响应
            if self.args.quiet:
                print(f"{response}")
                
            # 将响应存储在agent_app中，以便调用者可以访问
            agent_app._cli_response = response
            
            # 注意：这里不再使用SystemExit，让上下文管理器正常返回
        except Exception as e:
            print(f"\n\nError sending message to agent '{agent_name}': {str(e)}")
            raise SystemExit(1)
