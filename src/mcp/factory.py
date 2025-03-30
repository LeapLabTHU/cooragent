"""
Factory functions for creating agent and workflow instances.
"""

from typing import Any, Callable, Dict, Optional, TypeVar

from mcp_agent.agents.agent import Agent
from mcp_agent.app import MCPApp
from mcp_agent.core.agent_types import AgentConfig, AgentType
from mcp_agent.core.agent_utils import get_agent_instances, log_agent_load, unwrap_proxy
from mcp_agent.core.exceptions import AgentConfigError
from mcp_agent.core.proxies import (
    BaseAgentProxy,
    ChainProxy,
    LLMAgentProxy,
    RouterProxy,
    WorkflowProxy,
)
from mcp_agent.core.types import AgentOrWorkflow, ProxyDict
from mcp_agent.core.validation import get_dependencies
from mcp_agent.event_progress import ProgressAction
from mcp_agent.workflows.evaluator_optimizer.evaluator_optimizer import (
    EvaluatorOptimizerLLM,
    QualityRating,
)
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.model_factory import ModelFactory
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator
from mcp_agent.workflows.parallel.parallel_llm import ParallelLLM
from mcp_agent.workflows.router.router_llm import LLMRouter

T = TypeVar("T")  # For the wrapper classes


def create_proxy(app: MCPApp, name: str, instance: AgentOrWorkflow, agent_type: str) -> BaseAgentProxy:
    """Create appropriate proxy type based on agent type and validate instance type

    Args:
        app: The MCPApp instance
        name: Name of the agent/workflow
        instance: The agent or workflow instance
        agent_type: Type from AgentType enum values

    Returns:
        Appropriate proxy type wrapping the instance

    Raises:
        TypeError: If instance type doesn't match expected type for agent_type
    """
    if agent_type not in [
        AgentType.PARALLEL.value,
        AgentType.EVALUATOR_OPTIMIZER.value,
        AgentType.CHAIN.value,
    ]:
        log_agent_load(app, name)
    if agent_type == AgentType.BASIC.value:
        if not isinstance(instance, Agent):
            raise TypeError(f"Expected Agent instance for {name}, got {type(instance)}")
        return LLMAgentProxy(app, name, instance)
    elif agent_type == AgentType.ORCHESTRATOR.value:
        if not isinstance(instance, Orchestrator):
            raise TypeError(f"Expected Orchestrator instance for {name}, got {type(instance)}")
        return WorkflowProxy(app, name, instance)
    elif agent_type == AgentType.PARALLEL.value:
        if not isinstance(instance, ParallelLLM):
            raise TypeError(f"Expected ParallelLLM instance for {name}, got {type(instance)}")
        return WorkflowProxy(app, name, instance)
    elif agent_type == AgentType.EVALUATOR_OPTIMIZER.value:
        if not isinstance(instance, EvaluatorOptimizerLLM):
            raise TypeError(f"Expected EvaluatorOptimizerLLM instance for {name}, got {type(instance)}")
        return WorkflowProxy(app, name, instance)
    elif agent_type == AgentType.ROUTER.value:
        if not isinstance(instance, LLMRouter):
            raise TypeError(f"Expected LLMRouter instance for {name}, got {type(instance)}")
        return RouterProxy(app, name, instance)
    elif agent_type == AgentType.CHAIN.value:
        # Chain proxy is directly returned from _create_agents_by_type
        # No need for type checking as it's already a ChainProxy
        return instance
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def get_model_factory(
    context,
    model: Optional[str] = None,
    request_params: Optional[RequestParams] = None,
    default_model: Optional[str] = None,
    cli_model: Optional[str] = None,
) -> Any:
    """
    Get model factory using specified or default model.
    Model string is parsed by ModelFactory to determine provider and reasoning effort.

    Args:
        context: Application context
        model: Optional model specification string (highest precedence)
        request_params: Optional RequestParams to configure LLM behavior
        default_model: Default model from configuration
        cli_model: Model specified via command line

    Returns:
        ModelFactory instance for the specified or default model
    """
    # Config has lowest precedence
    model_spec = default_model or context.config.default_model

    # Command line override has next precedence
    if cli_model:
        model_spec = cli_model

    # Model from decorator has highest precedence
    if model:
        model_spec = model

    # Update or create request_params with the final model choice
    if request_params:
        request_params = request_params.model_copy(update={"model": model_spec})
    else:
        request_params = RequestParams(model=model_spec)

    # Let model factory handle the model string parsing and setup
    return ModelFactory.create_factory(model_spec, request_params=request_params)


async def create_agents_by_type(
    app_instance: MCPApp,
    agents_dict: Dict[str, Dict[str, Any]],
    agent_type: AgentType,
    active_agents: ProxyDict = None,
    model_factory_func: Callable = None,
    **kwargs,
) -> ProxyDict:
    """
    Generic method to create agents of a specific type.

    Args:
        app_instance: The main application instance
        agents_dict: Dictionary of agent configurations
        agent_type: Type of agents to create
        active_agents: Dictionary of already created agents/proxies (for dependencies)
        model_factory_func: Function for creating model factories
        **kwargs: Additional type-specific parameters

    Returns:
        Dictionary of initialized agents wrapped in appropriate proxies
    """
    if active_agents is None:
        active_agents = {}

    # Create a dictionary to store the initialized agents
    result_agents = {}

    # Get all agents of the specified type
    for name, agent_data in agents_dict.items():
        if agent_data["type"] == agent_type.value:
            # Get common configuration
            config = agent_data["config"]

            # Type-specific initialization
            if agent_type == AgentType.BASIC:
                # Get the agent name for special handling
                agent_name = agent_data["config"].name
                agent = Agent(
                    config=config,
                    context=app_instance.context,
                )
                await agent.initialize()

                llm_factory = model_factory_func(
                    model=config.model,
                    request_params=config.default_request_params,
                )
                agent._llm = await agent.attach_llm(llm_factory)
                # Store the agent
                instance = agent

            elif agent_type == AgentType.ORCHESTRATOR:
                # Get base params configured with model settings
                base_params = config.default_request_params.model_copy() if config.default_request_params else RequestParams()
                base_params.use_history = False  # Force no history for orchestrator

                # Get the child agents - need to unwrap proxies and validate LLM config
                child_agents = []
                for agent_name in agent_data["child_agents"]:
                    proxy = active_agents[agent_name]
                    instance = unwrap_proxy(proxy)
                    # Validate basic agents have LLM
                    if isinstance(instance, Agent):
                        if not hasattr(instance, "_llm") or not instance._llm:
                            raise AgentConfigError(
                                f"Agent '{agent_name}' used by orchestrator '{name}' missing LLM configuration",
                                "All agents must be fully configured with LLMs before being used in an orchestrator",
                            )
                    child_agents.append(instance)

                # Create a properly configured planner agent
                planner_config = AgentConfig(
                    name=f"{name}",  # Use orchestrator name as prefix
                    instruction=config.instruction
                    or """
                    You are an expert planner. Given an objective task and a list of MCP servers (which are collections of tools)
                    or Agents (which are collections of servers), your job is to break down the objective into a series of steps,
                    which can be performed by LLMs with access to the servers or agents.
                    """,
                    servers=[],  # Planner doesn't need server access
                    model=config.model,
                    default_request_params=base_params,
                )
                planner_agent = Agent(
                    config=planner_config,
                    context=app_instance.context,
                )
                planner_factory = model_factory_func(
                    model=config.model,
                    request_params=config.default_request_params,
                )

                planner = await planner_agent.attach_llm(planner_factory)
                # Create the orchestrator with pre-configured planner
                instance = Orchestrator(
                    name=config.name,
                    planner=planner,  # Pass pre-configured planner
                    available_agents=child_agents,
                    context=app_instance.context,
                    request_params=planner.default_request_params,  # Base params already include model settings
                    plan_type=agent_data.get("plan_type", "full"),  # Get plan_type from agent_data
                    verb=ProgressAction.PLANNING,
                )

            elif agent_type == AgentType.EVALUATOR_OPTIMIZER:
                # Get the referenced agents - unwrap from proxies
                generator = unwrap_proxy(active_agents[agent_data["generator"]])
                evaluator = unwrap_proxy(active_agents[agent_data["evaluator"]])

                if not generator or not evaluator:
                    raise ValueError(f"Missing agents for workflow {name}: generator={agent_data['generator']}, evaluator={agent_data['evaluator']}")

                # Get model from generator if it's an Agent, or from config otherwise
                optimizer_model = None
                if isinstance(generator, Agent):
                    optimizer_model = generator.config.model
                elif hasattr(generator, "_sequence") and hasattr(generator, "_agent_proxies"):
                    # For ChainProxy, use the config model directly
                    optimizer_model = config.model

                instance = EvaluatorOptimizerLLM(
                    name=config.name,  # Pass name from config
                    generator=generator,
                    evaluator=evaluator,
                    min_rating=QualityRating[agent_data["min_rating"]],
                    max_refinements=agent_data["max_refinements"],
                    llm_factory=model_factory_func(model=optimizer_model),
                    context=app_instance.context,
                    instruction=config.instruction,  # Pass any custom instruction
                )

            elif agent_type == AgentType.ROUTER:
                # Get the router's agents - unwrap proxies
                router_agents = get_agent_instances(agent_data["agents"], active_agents)

                # Create the router with proper configuration
                llm_factory = model_factory_func(
                    model=config.model,
                    request_params=config.default_request_params,
                )

                instance = LLMRouter(
                    name=config.name,
                    llm_factory=llm_factory,
                    agents=router_agents,
                    server_names=config.servers,
                    context=app_instance.context,
                    default_request_params=config.default_request_params,
                    verb=ProgressAction.ROUTING,  # Set verb for progress display
                )

            elif agent_type == AgentType.CHAIN:
                # Get the sequence from either parameter
                sequence = agent_data.get("sequence", agent_data.get("agents", []))

                # Auto-generate instruction if not provided or if it's just the default
                default_instruction = f"Chain of agents: {', '.join(sequence)}"

                # If user provided a custom instruction, use that
                # Otherwise, generate a description based on the sequence and their servers
                if config.instruction == default_instruction:
                    # Get all agent names in the sequence
                    agent_names = []
                    all_servers = set()

                    # Collect information about the agents and their servers
                    for agent_name in sequence:
                        if agent_name in active_agents:
                            agent_proxy = active_agents[agent_name]
                            if hasattr(agent_proxy, "_agent"):
                                # For LLMAgentProxy
                                agent_instance = agent_proxy._agent
                                agent_names.append(agent_name)
                                if hasattr(agent_instance, "server_names"):
                                    all_servers.update(agent_instance.server_names)
                            elif hasattr(agent_proxy, "_workflow"):
                                # For WorkflowProxy
                                agent_names.append(agent_name)

                    # Generate a better description
                    if agent_names:
                        server_part = f" with access to servers: {', '.join(sorted(all_servers))}" if all_servers else ""
                        config.instruction = f"Sequence of agents: {', '.join(agent_names)}{server_part}."

                # Create a ChainProxy without needing a new instance
                # Just pass the agent proxies and sequence
                instance = ChainProxy(app_instance, name, sequence, active_agents)
                # Set continue_with_final behavior from configuration
                instance._continue_with_final = agent_data.get("continue_with_final", True)
                # Set cumulative behavior from configuration
                instance._cumulative = agent_data.get("cumulative", False)

            elif agent_type == AgentType.PARALLEL:
                fan_out_agents = get_agent_instances(agent_data["fan_out"], active_agents)

                # Get fan-in agent - unwrap proxy
                fan_in_agent = unwrap_proxy(active_agents[agent_data["fan_in"]])

                # Create the parallel workflow
                llm_factory = model_factory_func(config.model)
                instance = ParallelLLM(
                    name=config.name,
                    instruction=config.instruction,
                    fan_out_agents=fan_out_agents,
                    fan_in_agent=fan_in_agent,
                    context=app_instance.context,
                    llm_factory=llm_factory,
                    default_request_params=config.default_request_params,
                    include_request=agent_data.get("include_request", True),
                )

            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")

            # Create the appropriate proxy and store in results
            result_agents[name] = create_proxy(app_instance, name, instance, agent_type.value)

    return result_agents


async def create_basic_agents(
    app_instance: MCPApp,
    agents_dict: Dict[str, Dict[str, Any]],
    model_factory_func: Callable,
) -> ProxyDict:
    """
    Create and initialize basic agents with their configurations.

    Args:
        app_instance: The main application instance
        agents_dict: Dictionary of agent configurations
        model_factory_func: Function for creating model factories

    Returns:
        Dictionary of initialized basic agents wrapped in appropriate proxies
    """
    return await create_agents_by_type(
        app_instance,
        agents_dict,
        AgentType.BASIC,
        model_factory_func=model_factory_func,
    )


async def create_agents_in_dependency_order(
    app_instance: MCPApp,
    agents_dict: Dict[str, Dict[str, Any]],
    active_agents: ProxyDict,
    agent_type: AgentType,
    model_factory_func: Callable,
) -> ProxyDict:
    """
    Create agents in dependency order to avoid circular references.
    Works for both Parallel and Chain workflows.

    Args:
        app_instance: The main application instance
        agents_dict: Dictionary of agent configurations
        active_agents: Dictionary of already created agents/proxies
        agent_type: Type of agents to create (AgentType.PARALLEL or AgentType.CHAIN)
        model_factory_func: Function for creating model factories

    Returns:
        Dictionary of initialized agents
    """
    result_agents = {}
    visited = set()

    # Get all agents of the specified type
    agent_names = [name for name, agent_data in agents_dict.items() if agent_data["type"] == agent_type.value]

    # Create agents in dependency order
    for name in agent_names:
        # Get ordered dependencies if not already processed
        if name not in visited:
            try:
                ordered_agents = get_dependencies(name, agents_dict, visited, set(), agent_type)
            except ValueError as e:
                raise ValueError(f"Error creating {agent_type.name.lower()} agent {name}: {str(e)}")

            # Create each agent in order
            for agent_name in ordered_agents:
                if agent_name not in result_agents:
                    # Create one agent at a time using the generic method
                    agent_result = await create_agents_by_type(
                        app_instance,
                        agents_dict,
                        agent_type,
                        active_agents,
                        model_factory_func=model_factory_func,
                        agent_name=agent_name,
                    )
                    if agent_name in agent_result:
                        result_agents[agent_name] = agent_result[agent_name]

    return result_agents
