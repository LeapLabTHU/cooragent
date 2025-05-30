#!/usr/bin/env python
import os
import json
import asyncio
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.theme import Theme
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
from src.workflow.cache import workflow_cache
import functools
import shlex
import platform
import atexit
import logging
from config.global_variables import agents_dir
from src.workflow.polish_task import polish_agent

logging.basicConfig(level=logging.INFO)
load_dotenv()

from src.interface.agent import *
from src.service.app import Server

if platform.system() == "Windows":
    import collections
    collections.Callable = collections.abc.Callable
    from pyreadline import Readline
    readline = Readline()
else:
    import readline

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "command": "bold yellow",
    "highlight": "bold cyan",
    "agent_name": "bold blue",
    "agent_nick_name": "bold magenta",
    "agent_desc": "green",
    "agent_type": "magenta",
    "tool_name": "bold blue",
    "tool_desc": "green",
    "user_msg": "bold white on blue",
    "assistant_msg": "bold black on green"
})

# Create Rich console object for beautified output
console = Console(theme=custom_theme)

_pending_line = ''

def direct_print(text):
    global _pending_line
    if not text:
        return
        
    text_to_print = str(text)
    
    # Handle special characters (< and >)
    if '<' in text_to_print or '>' in text_to_print:
        parts = []
        i = 0
        while i < len(text_to_print):
            if text_to_print[i] == '<':
                end_pos = text_to_print.find('>', i)
                if end_pos > i:
                    parts.append(text_to_print[i:end_pos+1])
                    i = end_pos + 1
                else:
                    parts.append(text_to_print[i])
                    i += 1
            else:
                parts.append(text_to_print[i])
                i += 1
        
        text_to_print = ''.join(parts)
    
    _pending_line += text_to_print
    
    while '\n' in _pending_line:
        pos = _pending_line.find('\n')
        line = _pending_line[:pos+1]  
        sys.stdout.write(line)
        sys.stdout.flush()
        _pending_line = _pending_line[pos+1:]

def flush_pending():
    global _pending_line
    if _pending_line:
        sys.stdout.write(_pending_line)
        sys.stdout.flush()
        _pending_line = ''

def stream_print(text, **kwargs):
    """Stream print text, ensuring immediate display. Automatically detects and renders Markdown format."""
    if kwargs.get("end", "\n") == "" and not kwargs.get("highlight", True):
        if text:
            sys.stdout.write(str(text))
            sys.stdout.flush()
    else:

        if isinstance(text, str) and _is_likely_markdown(text):
            try:
                plain_text = Text.from_markup(text).plain
                if plain_text.strip():
                    md = Markdown(plain_text)
                    console.print(md, **kwargs)
                else:
                    console.print(text, **kwargs)
            except Exception:
                 console.print(text, **kwargs)
        else:
            console.print(text, **kwargs)
        sys.stdout.flush()

def _is_likely_markdown(text):
    """Use simple heuristics to determine if the text is likely Markdown."""
    return any(marker in text for marker in ['\n#', '\n*', '\n-', '\n>', '```', '**', '__', '`', '[', '](', '![', '](', '<a href', '<img src'])

HISTORY_FILE = os.path.expanduser("~/.cooragent_history")

def _init_readline():
    try:
        readline.parse_and_bind(r'"\C-?": backward-kill-word') 
        readline.parse_and_bind(r'"\e[3~": delete-char')        
        readline.parse_and_bind('set editing-mode emacs') 
        readline.parse_and_bind('set horizontal-scroll-mode on')
        readline.parse_and_bind('set bell-style none')
        
        history_dir = os.path.dirname(HISTORY_FILE)
        if not os.path.exists(history_dir):
            os.makedirs(history_dir, exist_ok=True)
        
        if not os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                pass
        
        try:
            readline.read_history_file(HISTORY_FILE)
        except:
            pass
        
        readline.set_history_length(1000)
        atexit.register(_save_history)
        
    except Exception as e:
        console.print(f"[warning]Failed to initialize command history: {str(e)}[/warning]")

def _save_history():
    """Safely save command history"""
    try:
        readline.write_history_file(HISTORY_FILE)
    except Exception as e:
        console.print(f"[warning]Unable to save command history: {str(e)}[/warning]")


def print_banner():
    banner = """
							    ╔═══════════════════════════════════════════════════════════════════════════════╗
							    ║                                                                               ║
							    ║        ██████╗ ██████╗  ██████╗ ██████╗  █████╗  ██████╗ ███████╗███╗   ██╗████████╗    
							    ║       ██╔════╝██╔═══██╗██╔═══██╗██╔══██╗██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    
							    ║       ██║     ██║   ██║██║   ██║██████╔╝███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       
							    ║       ██║     ██║   ██║██║   ██║██╔══██╗██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       
							    ║       ╚██████╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       
							    ║        ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       
							    ║                                                                               ║
							    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(Text(banner, style="bold cyan"), border_style="green"))
    console.print("Welcome to [highlight]CoorAgent[/highlight]! CoorAgent is an AI agent collaboration community. Here, you can create specific agents with a single sentence and collaborate with other agents to complete complex tasks. Agents can be combined freely, creating infinite possibilities. You can also publish your agents to the community and share them to anyone!\n", justify="center")


def async_command(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def init_server(ctx):
    """global init function"""
    if not ctx.obj.get('_initialized', False):
        with console.status("[bold green]Initializing server...[/]", spinner="dots"):
            _init_readline()
            print_banner()
            ctx.obj['server'] = Server()
            ctx.obj['_initialized'] = True
        console.print("[success]✓ Server initialized successfully[/]")

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """CoorAgent command-line tool"""
    ctx.ensure_object(dict)
    init_server(ctx)
    
    if ctx.invoked_subcommand is None:
        console.print("Enter 'exit' to quit interactive mode\n")
        should_exit = False
        while not should_exit:
            try:
                command = input("\001\033[1;36m\002CoorAgent>\001\033[0m\002 ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ('exit', 'quit'):
                    console.print("[success]Goodbye![/]")
                    should_exit = True
                    flush_pending()  # Flush buffer before exiting
                    break
                
                if command and not command.lower().startswith(('exit', 'quit')):
                    readline.add_history(command)
                
                args = shlex.split(command)
                with cli.make_context("cli", args, parent=ctx) as sub_ctx:
                    cli.invoke(sub_ctx)
                    
            except Exception as e:
                console.print(f"[danger]Error: {str(e)}[/]")
        return


@cli.command()
@click.pass_context
@click.option('--user-id', '-u', default="test", help='User ID')
@click.option('--task-type', '-t', required=True, 
              type=click.Choice([task_type.value for task_type in TaskType]), 
              help='Task type (options: agent_factory, agent_workflow)')
@click.option('--message', '-m', required=True, multiple=True, help='Message content (use multiple times for multiple messages)')
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
@click.option('--deep-thinking/--no-deep-thinking', default=True, help='Enable deep thinking mode')
@click.option('--search-before-planning/--no-search-before-planning', default=False, help='Enable search before planning')
@click.option('--agents', '-a', multiple=True, help='List of collaborating Agents (use multiple times to add multiple Agents)')
@async_command
async def run(ctx, user_id, task_type, message, debug, deep_thinking, search_before_planning, agents):
    """Run the agent workflow"""
    server = ctx.obj['server']
    
    config_table = Table(title="Workflow Configuration", show_header=True, header_style="bold magenta")
    config_table.add_column("Parameter", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_row("User ID", user_id)
    config_table.add_row("Task Type", task_type)
    config_table.add_row("Debug Mode", "✅ Enabled" if debug else "❌ Disabled")
    config_table.add_row("Deep Thinking", "✅ Enabled" if deep_thinking else "❌ Disabled")
    config_table.add_row("Search Before Planning", "✅ Enabled" if search_before_planning else "❌ Disabled")
    console.print(config_table)
    
    msg_table = Table(title="Message History", show_header=True, header_style="bold magenta")
    msg_table.add_column("Role", style="cyan")
    msg_table.add_column("Content", style="green")
    for i, msg in enumerate(message):
        role = "User" if i % 2 == 0 else "Assistant"
        style = "user_msg" if i % 2 == 0 else "assistant_msg"
        msg_table.add_row(role, Text(msg, style=style))
    console.print(msg_table)
    
    messages = []
    for i, msg in enumerate(message):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": msg})
    
    request = AgentRequest(
        user_id=user_id,
        lang="en",
        task_type=task_type,
        messages=messages,
        debug=debug,
        deep_thinking_mode=deep_thinking,
        search_before_planning=search_before_planning,
        coor_agents=list(agents)
    )
    
    console.print(Panel.fit("[highlight]Workflow execution started[/highlight]", title="CoorAgent", border_style="cyan"))
    
    current_content = ""
    json_buffer = ""  
    in_json_block = False
    live_mode = True
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
        refresh_per_second=2
    ) as progress:
        task = progress.add_task("[green]Processing request...", total=None)
        
        async for chunk in server._run_agent_workflow(request):
            event_type = chunk.get("event")
            data = chunk.get("data", {})
            
            if event_type == "start_of_agent":
                if current_content:
                    console.print(current_content, end="", highlight=False)
                    current_content = ""
                
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "")
                if agent_name :
                    console.print("\n")
                    progress.update(task, description=f"[green]Starting execution: {agent_name}...")
                    console.print(f"[agent_name]>>> {agent_name} starting execution...[/agent_name]")
                    console.print("")
                    
            elif event_type == "end_of_agent":
                if current_content:
                    console.print(current_content, end="", highlight=False)
                    current_content = ""
                
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")  
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                agent_name = data.get("agent_name", "")
                if agent_name:
                    console.print("\n")
                    progress.update(task, description=f"[green]Execution finished: {agent_name}...")
                    console.print(f"[agent_name]<<< {agent_name} execution finished[/agent_name]")
                    console.print("")
            
            elif event_type == "messages":
                delta = data.get("delta", {})
                content = delta.get("content", "")
                reasoning = delta.get("reasoning_content", "")
                agent_name = data.get("agent_name", "")

                
                if agent_name:
                    console.print("\n")
                    progress.update(task, description=f"[green]Executing: {agent_name}...")
                    progress.update(task, description=f"[agent_name]>>> {agent_name} executing...[/agent_name]")
                    console.print("")
                if content and (content.strip().startswith("{") or in_json_block):
                    if not in_json_block:
                        in_json_block = True
                        json_buffer = ""
                    
                    json_buffer += content
                    
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        
                        if current_content:
                            console.print(current_content, end="", highlight=False)
                            current_content = ""
                        
                        console.print("")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                        json_buffer = ""
                        in_json_block = False
                    except:
                        pass
                elif content:
                    if live_mode:
                        if not content: 
                            continue
    
                        direct_print(content)

                    else:
                        current_content += content
                
                if reasoning:
                    stream_print(f"\n[info]Thinking process: {reasoning}[/info]")
                

            elif event_type == "new_agent_created":
                new_agent_name = data.get("new_agent_name", "")
                agent_obj = data.get("agent_obj", None)
                console.print(f"[new_agent_name]>>> {new_agent_name} created successfully...")
                console.print(f"[new_agent]>>> Configuration: ")
                syntax = Syntax(agent_obj, "json", theme="monokai", line_numbers=False)
                console.print(syntax)


            elif event_type == "end_of_workflow":
                if current_content:
                    console.print(current_content, end="", highlight=False)
                    current_content = ""
                
                if in_json_block and json_buffer:
                    try:
                        parsed_json = json.loads(json_buffer)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n{json_buffer}")
                    json_buffer = ""
                    in_json_block = False
                
                console.print("")
                progress.update(task, description="[success]Workflow execution finished!")
                console.print(Panel.fit("[success]Workflow execution finished![/success]", title="CoorAgent", border_style="green"))
                
                    
    
    console.print(Panel.fit("[success]Workflow execution finished![/success]", title="CoorAgent", border_style="green"))


@cli.command()
@click.pass_context
@click.option('--user-id', '-u', default="test", help='User ID')
@click.option('--match', '-m', default="", help='Match string')
@async_command 
async def list_agents(ctx, user_id, match):
    """List user's Agents"""
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Fetching Agent list...", total=None)
        
        request = listAgentRequest(user_id=user_id, match=match)
        
        table = Table(title=f"Agent list for user [highlight]{user_id}[/highlight]", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("Name", style="agent_name")
        table.add_column("Nickname", style="agent_nick_name")
        table.add_column("Description", style="agent_desc")
        table.add_column("Tools", style="agent_type")
        
        count = 0
        async for agent_json in server._list_agents(request):
            try:
                agent = json.loads(agent_json)
                tools = []
                for tool in agent.get("selected_tools", []):
                    tools.append(tool.get("name", ""))
                table.add_row(agent.get("agent_name", ""), agent.get("nick_name", ""), agent.get("description", ""), ', '.join(tools))
                count += 1
            except:
                stream_print(f"[danger]Parsing error: {agent_json}[/danger]")
        
        progress.update(task, description=f"[success]Fetched {count} Agents!")
        
        if count == 0:
            stream_print(Panel(f"No matching Agents found", title="Result", border_style="yellow"))
        else:
            stream_print(table)


@cli.command()
@click.pass_context
@async_command 
async def list_default_agents(ctx):
    """List default Agents"""
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Fetching default Agent list...", total=None)
        
        table = Table(title="Default Agent List", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("Name", style="agent_name")
        table.add_column("Nickname", style="agent_nick_name")
        table.add_column("Description", style="agent_desc")
        
        count = 0
        async for agent_json in server._list_default_agents():
            try:
                agent = json.loads(agent_json)
                table.add_row(agent.get("agent_name", ""),agent.get("nick_name", ""), agent.get("description", ""))
                count += 1
            except:
                stream_print(f"[danger]Parsing error: {agent_json}[/danger]")
        
        progress.update(task, description=f"[success]Fetched {count} default Agents!")
        stream_print(table)


@cli.command()
@click.pass_context
@async_command  
async def list_default_tools(ctx):
    """List default tools"""
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Fetching default tool list...", total=None)
        
        table = Table(title="Default Tool List", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("Name", style="tool_name")
        table.add_column("Description", style="tool_desc")
        
        count = 0
        async for tool_json in server._list_default_tools():
            try:
                tool = json.loads(tool_json)
                table.add_row(tool.get("name", ""), tool.get("description", ""))
                count += 1
            except:
                stream_print(f"[danger]Parsing error: {tool_json}[/danger]")
        
        progress.update(task, description=f"[success]Fetched {count} default tools!")
        stream_print(table)


@cli.command()
@click.pass_context
@click.option('--agent-name', '-n', required=True, help='Name of the Agent to edit')
@click.option('--user-id', '-u', required=True, help='User ID')
@click.option('--interactive/--no-interactive', '-i/-I', default=True, help='Use interactive mode')
@async_command
async def edit_agent(ctx, agent_name, user_id, interactive):
    """Edit an existing Agent interactively"""
    server = ctx.obj['server']
    stream_print(Panel.fit(f"[highlight]Fetching configuration for {agent_name}...[/highlight]", border_style="cyan"))
    original_config = None
    try:
        async for agent_json in server._list_agents(listAgentRequest(user_id=user_id, match=agent_name)):
            agent = json.loads(agent_json)
            if agent.get("agent_name") == agent_name:
                original_config = agent
                break
        if not original_config:
            stream_print(f"[danger]Agent not found: {agent_name}[/danger]")
            return
    except Exception as e:
        stream_print(f"[danger]Failed to fetch configuration: {str(e)}[/danger]")
        return

    def show_current_config():
        stream_print(Panel.fit(
            f"[agent_name]Name:[/agent_name] {original_config.get('agent_name', '')}\n"
            f"[agent_nick_name]Nickname:[/agent_nick_name] {original_config.get('nick_name', '')}\n"
            f"[agent_desc]Description:[/agent_desc] {original_config.get('description', '')}\n"
            f"[tool_name]Tools:[/tool_name] {', '.join([t.get('name', '') for t in original_config.get('selected_tools', [])])}\n"
            f"[highlight]Prompt:[/highlight]\n{original_config.get('prompt', '')}",
            title="Current Configuration",
            border_style="blue"
        ))
    
    show_current_config()

    modified_config = original_config.copy()
    while interactive:
        console.print("\nSelect content to modify:")
        console.print("1 - Modify Nickname")
        console.print("2 - Modify Description")
        console.print("3 - Modify Tool List")
        console.print("4 - Modify Prompt")
        console.print("5 - Preview Changes")
        console.print("0 - Save and Exit")
        
        choice = Prompt.ask(
            "Enter option",
            choices=["0", "1", "2", "3", "4", "5"],
            show_choices=False
        )
        
        if choice == "1":
            new_name = Prompt.ask(
                "Enter new nickname", 
                default=modified_config.get('nick_name', ''),
                show_default=True
            )
            modified_config['nick_name'] = new_name
        
        elif choice == "2":
            new_desc = Prompt.ask(
                "Enter new description", 
                default=modified_config.get('description', ''),
                show_default=True
            )
            modified_config['description'] = new_desc
        
        elif choice == "3":
            current_tools = [t.get('name') for t in modified_config.get('selected_tools', [])]
            stream_print(f"Current tools: {', '.join(current_tools)}")
            new_tools = Prompt.ask(
                "Enter new tool list (comma-separated)",
                default=", ".join(current_tools),
                show_default=True
            )
            modified_config['selected_tools'] = [
                {"name": t.strip(), "description": ""} 
                for t in new_tools.split(',') 
                if t.strip()
            ]
        
        elif choice == "4":
            console.print("Enter new prompt (type 'END' to finish):")
            lines = []
            while True:
                line = Prompt.ask("> ", default="")
                if line == "END":
                    break
                lines.append(line)
            modified_config['prompt'] = "\n".join(lines)
        
        elif choice == "5":
            show_current_config()
            stream_print(Panel.fit(
                f"[agent_name]New Name:[/agent_name] {modified_config.get('agent_name', '')}\n"
                f"[nick_name]New Nickname:[/nick_name] {modified_config.get('nick_name', '')}\n"
                f"[agent_desc]New Description:[/agent_desc] {modified_config.get('description', '')}\n"
                f"[tool_name]New Tools:[/tool_name] {', '.join([t.get('name', '') for t in modified_config.get('selected_tools', [])])}\n"
                f"[highlight]New Prompt:[/highlight]\n{modified_config.get('prompt', '')}",
                title="Modified Configuration Preview",
                border_style="yellow"
            ))
        
        elif choice == "0":
            if Confirm.ask("Confirm saving changes?"):
                try:
                    agent_request = Agent(
                        user_id=original_config.get('user_id', ''),
                        nick_name=modified_config['nick_name'],
                        agent_name=modified_config['agent_name'],
                        description=modified_config['description'],
                        selected_tools=modified_config['selected_tools'],
                        prompt=modified_config['prompt'],
                        llm_type=original_config.get('llm_type', 'basic')
                    )
                    
                    async for result in server._edit_agent(agent_request):
                        res = json.loads(result)
                        if res.get("result") == "success":
                            stream_print(Panel.fit("[success]Agent updated successfully![/success]", border_style="green"))
                        else:
                            stream_print(f"[danger]Update failed: {res.get('result', 'Unknown error')}[/danger]")
                    return
                except Exception as e:
                    stream_print(f"[danger]Error occurred during save: {str(e)}[/danger]")
            else:
                stream_print("[warning]Modifications cancelled[/warning]")
            return


@cli.command(name="polish")
@click.pass_context
@click.option('--user-id', '-u', required=True, help='User ID')
@click.option('--match', '-m', help='Match string')
@click.option('--interactive/--no-interactive', '-i/-I', default=True, help='Use interactive mode')
@async_command
async def polish(ctx, user_id, match, interactive):
    """Edit an existing Agent interactively"""
    server = ctx.obj['server']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Fetching Workflow list...", total=None)
        
        request = listAgentRequest(user_id=user_id, match=match)
        
        table = Table(title=f"Workflow list for user [highlight]{user_id}[/highlight]", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("ID", style="tool_desc")
        table.add_column("Workflow ID", style="tool_desc")
        table.add_column("Lap", style="tool_desc")
        table.add_column("Version", style="tool_desc")
        table.add_column("Graph", style="tool_desc")
        table.add_column("Planning Steps", style="agent_nick_name")

        
        count = 0
        workflow_list = server._list_workflow(request)
        for workflow in workflow_list:
            try:
                planning = json.loads(workflow.get("planning_steps", ""))
                steps = planning['steps']
                table.add_row(str(count), workflow.get("workflow_id", ""), str(workflow.get("lap", "")), str(workflow.get("version", "")), json.dumps(workflow.get("graph", ""), indent=2, ensure_ascii=False), json.dumps(steps, indent=2, ensure_ascii=False))
                count += 1
            except:
                stream_print(f"[danger]Parsing error: {workflow}[/danger]")
        
        progress.update(task, description=f"[success]Fetched {count} workflow!")
        
        if count == 0:
            stream_print(Panel(f"No matching workflow found", title="Result", border_style="yellow"))
        else:
            stream_print(table)    
    
    
    while interactive:
        console.print("\n Select workflow by index to polish:")
        
        choice = Prompt.ask(
            "Enter workflow ID",
            choices=[str(i) for i in range(count)],
            show_choices=True
        )
        
        workflow_id = workflow_list[int(choice)]["workflow_id"]
        
        parts_to_edit_options = ["graph", "planning_steps"]
        console.print("Select part to edit:")
        for i, part_option in enumerate(parts_to_edit_options):
            console.print(f"{i+1} - {part_option}")

        part_choice_idx_str = Prompt.ask(
            "Enter part number",
            choices=[str(i+1) for i in range(len(parts_to_edit_options))],
            show_choices=False
        )
        part_to_edit = parts_to_edit_options[int(part_choice_idx_str) - 1]

        if part_to_edit == "graph":
            agents = workflow_cache.get_editable_agents((workflow_id))
            
            console.print("Select agent to edit:")
            for i, agent in enumerate(agents):
                console.print(f"{i+1} - {agent.agent_name}")

            agent_choice_idx_str = Prompt.ask(
                "Enter agent number",
                choices=[str(i+1) for i in range(len(agents))],
                show_choices=False 
            )
            agent_to_edit = agents[int(agent_choice_idx_str) - 1].agent_name
            
            agent_path = agents_dir / f"{agent_to_edit}.json"
            if not agent_path.exists():
                raise FileNotFoundError(f"agent {agent_to_edit} not found.")
            with open(agent_path, "r") as f:
                json_str = f.read()
                _agent = Agent.model_validate_json(json_str)

            def show_current_config(agent):
                stream_print(Panel.fit(
                    f"[agent_name]Name:[/agent_name] {agent.agent_name}\n"
                    f"[agent_nick_name]Nickname:[/agent_nick_name] {agent.nick_name}\n"
                    f"[agent_desc]Description:[/agent_desc] {agent.description}\n"
                    f"[tool_name]Tools:[/tool_name] {', '.join([t.name for t in agent.selected_tools])}\n"
                    f"[highlight]Prompt:[/highlight]\n{agent.prompt}",
                    title="Current Configuration",
                    border_style="blue"
                ))
            
            show_current_config(_agent)
            
            stop_polishing = False
            while not stop_polishing:
                agent_part_options = ["tools", "prompt"]
                console.print("Select part to edit:")
                for i, part_option in enumerate(agent_part_options):
                    console.print(f"{i+1} - {part_option}")

                part_choice_idx_str = Prompt.ask(
                    "Enter part number",
                    choices=[str(i+1) for i in range(len(agent_part_options))],
                    show_choices=False
                )
                part_to_edit = agent_part_options[int(part_choice_idx_str) - 1]            
                

                while True:
                    instruction = Prompt.ask(
                        "Enter your instruction",
                        show_default=True
                    )
                    content = await polish_agent(_agent, instruction, part_to_edit)
                    stream_print(f"polished {part_to_edit}: \n {content}")
                    if Confirm.ask("Confirm saving changes?"):
                        if Confirm.ask("Stop polishing?"):
                            stop_polishing = True
                        _agent.prompt = content
                        # agent_manager.update_agent(_agent)
                        break

            show_current_config(_agent)       
            
            if Confirm.ask("Confirm saving changes?"):
                    try:
                        async for result in server._edit_agent(_agent):
                            res = json.loads(result)
                            if res.get("result") == "success":
                                stream_print(Panel.fit("[success]Agent updated successfully![/success]", border_style="green"))
                            else:
                                stream_print(f"[danger]Update failed: {res.get('result', 'Unknown error')}[/danger]")
                        return
                    except Exception as e:
                        stream_print(f"[danger]Error occurred during save: {str(e)}[/danger]")
            else:
                stream_print("[warning]Modifications cancelled[/warning]")
                                 
    
            return

@cli.command(name="remove-agent")
@click.pass_context
@click.option('--agent-name', '-n', required=True, help='Name of the Agent to remove')
@click.option('--user-id', '-u', required=True, help='User ID')
@async_command
async def remove_agent(ctx, agent_name, user_id):
    """Remove the specified Agent"""
    server = ctx.obj['server']
    
    if not Confirm.ask(f"[warning]Are you sure you want to delete Agent '{agent_name}'? This action cannot be undone![/warning]", default=False):
        stream_print("[info]Operation cancelled[/info]")
        return
        
    stream_print(Panel.fit(f"[highlight]Deleting Agent: {agent_name}...[/highlight]", border_style="cyan"))

    try:
        request = RemoveAgentRequest(user_id=user_id, agent_name=agent_name)
        async for result_json in server._remove_agent(request):
            result = json.loads(result_json)
            if result.get("result") == "success":
                stream_print(Panel.fit(f"[success]✅ {result.get('message', 'Agent deleted successfully!')}[/success]", border_style="green"))
            else:
                stream_print(Panel.fit(f"[danger]❌ {result.get('message', 'Agent deletion failed!')}[/danger]", border_style="red"))
    except Exception as e:
        stream_print(Panel.fit(f"[danger]Error occurred during deletion: {str(e)}[/danger]", border_style="red"))


@cli.command()
def help():
    """Display help information"""
    help_table = Table(title="Help Information", show_header=False, border_style="cyan", width=100)
    help_table.add_column(style="bold cyan")
    help_table.add_column(style="green")
    
    help_table.add_row("[Command] run", "Run the agent workflow")
    help_table.add_row("  -u/--user-id", "User ID")
    help_table.add_row("  -t/--task-type", "Task type (agent_factory/agent_workflow)")
    help_table.add_row("  -m/--message", "Message content (use multiple times)")
    help_table.add_row("  --debug/--no-debug", "Enable/disable debug mode")
    help_table.add_row("  --deep-thinking/--no-deep-thinking", "Enable/disable deep thinking mode")
    help_table.add_row("  --search-before-planning/--no-search-before-planning", "Enable/disable search before planning (default: enabled)")
    help_table.add_row("  -a/--agents", "List of collaborating Agents")
    help_table.add_row()
    
    help_table.add_row("[Command] list-agents", "List user's Agents")
    help_table.add_row("  -u/--user-id", "User ID (required)")
    help_table.add_row("  -m/--match", "Match string")
    help_table.add_row()
    
    help_table.add_row("[Command] list-default-agents", "List default Agents")
    help_table.add_row("[Command] list-default-tools", "List default tools")
    help_table.add_row()
    
    help_table.add_row("[Command] edit-agent", "Interactively edit an Agent")
    help_table.add_row("  -n/--agent-name", "Agent name (required)")
    help_table.add_row("  -u/--user-id", "User ID (required)")
    help_table.add_row("  -i/--interactive", "Interactive mode (default: on)")
    help_table.add_row()
    
    help_table.add_row("[Command] remove-agent", "Remove the specified Agent")
    help_table.add_row("  -n/--agent-name", "Agent name (required)")
    help_table.add_row("  -u/--user-id", "User ID (required)")
    help_table.add_row()

    help_table.add_row("[Interactive Mode]", "Run cli.py directly to enter")
    help_table.add_row("  exit/quit", "Exit interactive mode")
    
    console.print(help_table)


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        stream_print("\n[warning]Operation cancelled[/warning]")
        flush_pending()
    except Exception as e:
        stream_print(f"\n[danger]An error occurred: {str(e)}[/danger]")
        flush_pending()
    finally:
        flush_pending()
