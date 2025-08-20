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
import signal
from config.global_variables import agents_dir
from src.workflow.polish_task import polish_agent
import traceback

logging.basicConfig(level=logging.INFO)
load_dotenv()

from src.interface.agent import *
from src.service.server import Server

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
    "assistant_msg": "bold black on green",
    "step_title": "bold magenta",
    "step_desc": "green",
    "step_note": "magenta",
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

def show_agent_config(config):
    stream_print(Panel.fit(
        f"[agent_name]Name:[/agent_name] {config.get('agent_name', '')}\n"
        f"[agent_nick_name]NickName:[/agent_nick_name] {config.get('nick_name', '')}\n"
        f"[agent_desc]Description:[/agent_desc] {config.get('description', '')}\n"
        f"[tool_name]Tools:[/tool_name] {', '.join([t.get('name', '') for t in config.get('selected_tools', [])])}\n"
        f"[highlight]Prompt:[/highlight]\n{config.get('prompt', '')}",
        title="Current Configuration",
        border_style="blue"
    ))
async def edit_agent_option(_agent: Agent, edit_option:list[str], original_config, modified_config, server: Server):
    all_edit_option = {
        'NickName': 'Modify NickName',
        'Description': 'Modify Description',
        'Tool': 'Modify Tool List',
        'Prompt': 'Modify Prompt',
        'Preview': 'Preview Changes',
        'Save': 'Save and Exit',
        'Exit': 'Only Exit'
    }
    choices = []
    console.print("\nSelect content to modify:")
    edit_option += ['Preview', 'Save', 'Exit']
    for index, option in enumerate(edit_option):
        console.print(f"{index + 1} - {all_edit_option[option]}")
        choices.append(str(index + 1))
    choice = Prompt.ask(
        "Enter option",
        choices=choices,
        show_choices=False
    )
    choice_option = edit_option[int(choice)-1]
    if choice_option == 'NickName':
        new_name = Prompt.ask(
            "Enter new NickName",
            default=modified_config.get('nick_name', ''),
            show_default=True
        )
        modified_config['nick_name'] = new_name
        return False

    elif choice_option == 'Description':
        new_desc = Prompt.ask(
            "Enter new description",
            default=modified_config.get('description', ''),
            show_default=True
        )
        modified_config['description'] = new_desc
        return False

    elif choice_option == 'Tool':

        async def use_ai_generate_prompt():
            if Confirm.ask("Whether to automatically update prompt?"):
                repeat = True
                while repeat:
                    polish_content = await polish_agent(_agent=_agent, part_to_edit='tool', tools=modified_config.get('selected_tools'))
                    stream_print(f"polished description: \n {polish_content['agent_description']}\n\n")
                    stream_print(f"polished prompt: \n {polish_content['prompt']}")
                    if not Confirm.ask("Do we need to regenerate the prompt?"):
                        repeat = False
                        if Confirm.ask("Confirm saving changes?"):
                            modified_config['description'] = polish_content['agent_description']
                            modified_config['prompt'] = polish_content['prompt']
                        else:
                            stream_print(f"[warning]The tool list may not match the prompt[/warning]")
            else:
                stream_print(f"[warning]The tool list may not match the prompt[/warning]")

        stream_print("[green]Fetching tool list...")
        default_tool_name = []
        default_tool_desc = {}
        async for tool_json in server._list_default_tools():
            try:
                default_tool = json.loads(tool_json)
                default_tool_name.append(default_tool.get('name'))
                default_tool_desc[default_tool.get('name')] = default_tool.get('description')
            except:
                stream_print(f"[danger]Parsing error: {tool_json}[/danger]")
        stream_print("[success]Fetched tools!")
        table = Table(title=f"Tool list for agent [highlight]{modified_config.get('nick_name')}[/highlight]", show_header=True, header_style="bold magenta", border_style="cyan")
        table.add_column("Number", style="tool_desc")
        table.add_column("Name", style="tool_desc")
        table.add_column("Description", style="tool_desc")
        current_tools = modified_config.get('selected_tools')
        agent_tool_names = []
        for num,tool in enumerate(current_tools):
            table.add_row(str(num), tool['name'], tool['description'])
            agent_tool_names.append(tool['name'])
        stream_print(table)
        _stop = False
        while not _stop:
            edit_tools_option = ["add tool","delete tool","view default tool list"]
            for i, part_option in enumerate(edit_tools_option):
                console.print(f"{i + 1} - {part_option}")
            choice_tools_option_idx = Prompt.ask(
                "Enter part number to select operation",
                choices=[str(i + 1) for i in range(len(edit_tools_option))],
                show_choices=False
            )
            if choice_tools_option_idx == '1':
                new_tools = Prompt.ask(
                    "Enter tool list to add (comma-separated)",
                    show_default=True
                )
                change_successful = False
                for t in new_tools.split(','):
                    if t.strip() not in agent_tool_names:
                        if t.strip() in default_tool_name:
                            modified_config['selected_tools'].append({"name": t.strip(), "description": default_tool_desc[t.strip()]})
                            change_successful = True
                        else:
                            stream_print(f"[danger]Error occurred during add:\n {t.strip()} does not exist in the default tool list[/danger]")
                    else:
                        stream_print(f"[warning]{t.strip()} already exists[/warning]")
                if change_successful:
                    await use_ai_generate_prompt()
                _stop = True
            elif choice_tools_option_idx == '2':
                del_tools = Prompt.ask(
                    "Enter tool list to delete (comma-separated)",
                    show_default=True
                )
                change_successful = False
                for t in del_tools.split(','):
                    if t.strip() in agent_tool_names:
                        for i,original_tool in enumerate(modified_config.get('selected_tools')):
                            if original_tool["name"] == t.strip():
                                modified_config['selected_tools'].pop(i)
                                change_successful = True
                                break
                    else:
                        stream_print(
                            f"[danger]Error occurred during delete:\n {t.strip()} does not exist in the agent tool list[/danger]")
                if change_successful:
                    await use_ai_generate_prompt()
                _stop = True
            elif choice_tools_option_idx == '3':
                table = Table(title="Default Tool List", show_header=True, header_style="bold magenta", border_style="cyan")
                table.add_column("Name", style="tool_name")
                table.add_column("Description", style="tool_desc")
                for tool_name in default_tool_name:
                    table.add_row(tool_name, default_tool_desc[tool_name])
                stream_print(table)
        return False

    elif choice_option == 'Prompt':
        console.print("Enter new prompt (type 'END' to finish):")
        lines = []
        while True:
            line = Prompt.ask("> ", default="")
            if line == "END":
                break
            lines.append(line)
        modified_config['prompt'] = "\n".join(lines)
        return False

    elif choice_option == 'Preview':
        show_agent_config(original_config)
        stream_print(Panel.fit(
            f"[agent_name]New Name:[/agent_name] {modified_config.get('agent_name', '')}\n"
            f"[nick_name]New NickName:[/nick_name] {modified_config.get('nick_name', '')}\n"
            f"[agent_desc]New Description:[/agent_desc] {modified_config.get('description', '')}\n"
            f"[tool_name]New Tools:[/tool_name] {', '.join([t.get('name', '') for t in modified_config.get('selected_tools', [])])}\n"
            f"[highlight]New Prompt:[/highlight]\n{modified_config.get('prompt', '')}",
            title="Modified Configuration Preview",
            border_style="yellow"
        ))
        return False

    elif choice_option == 'Save':
        if Confirm.ask("Confirm saving changes and exit?"):
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
                _agent.prompt = modified_config['prompt']
                _agent.description = modified_config['description']
                _agent.selected_tools = modified_config['selected_tools']
                async for result in server._edit_agent(agent_request):
                    res = json.loads(result)
                    if res.get("result") == "success":
                        stream_print(Panel.fit("[success]Agent updated successfully![/success]", border_style="green"))
                    else:
                        stream_print(f"[danger]Update failed: {res.get('result', 'Unknown error')}[/danger]")
                return True
            except Exception as e:
                stream_print(f"[danger]Error occurred during save: {str(e)}[/danger]")
                return True
        else:
            stream_print("[warning]Modifications cancelled[/warning]")
            return False
    elif choice_option == 'Exit':
        if Confirm.ask("Abandon any changes and exit?"):
            return True
        else:
            return False

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

def handle_sigint(signal, frame):
    console.print("[success]Goodbye![/]")
    flush_pending()  # Flush buffer before exiting
    sys.exit(0)


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

    signal.signal(signal.SIGINT, handle_sigint)
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


@cli.command(name="run-l")
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
async def run_launch(ctx, user_id, task_type, message, debug, deep_thinking, search_before_planning, agents,):
    """Run the agent workflow"""
    server: Server = ctx.obj['server']
    
    config_table = Table(title="Run Launch Configuration", show_header=True, header_style="bold magenta")
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
        coor_agents=list(agents),
        workmode="launch",
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
                # The pipeline needs to be flushed after the agent finishes
                flush_pending()

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


@cli.command(name="run-p")
@click.pass_context
@click.option('--user-id', '-u', default="test", help='User ID')
@click.option('--messages', '-m', default=[],  multiple=True, help='Message content (use multiple times for multiple messages)')
@click.option('--workflow-id', '-w', default="", help='Workflow ID')
@async_command
async def run_production(ctx, user_id, messages, workflow_id):
    """Run the agent workflow"""
    server: Server = ctx.obj['server']
 
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[green]Fetching Workflow list...", total=None)
        
        request = listAgentRequest(user_id=user_id, match=None)
        
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
                steps = workflow.get("planning_steps", [])
                if workflow_id:
                    if workflow.get("workflow_id") == workflow_id:
                        table.add_row(str(count), workflow.get("workflow_id", ""), str(workflow.get("lap", "")), str(workflow.get("version", "")), json.dumps(workflow.get("graph", ""), indent=2, ensure_ascii=False), json.dumps(steps, indent=2, ensure_ascii=False))
                        count += 1
                        break
                else:   
                    table.add_row(str(count), workflow.get("workflow_id", ""), str(workflow.get("lap", "")), str(workflow.get("version", "")), json.dumps(workflow.get("graph", ""), indent=2, ensure_ascii=False), json.dumps(steps, indent=2, ensure_ascii=False))
                    count += 1
            except Exception as e:
                logging.error(f"Error parsing workflow: {traceback.format_exc()}")
                stream_print(f"[danger]Parsing error: {workflow}[/danger]")
        
        progress.update(task, description=f"[success]Fetched {count} workflow!")
        
    if count == 0:
        stream_print(Panel(f"No matching workflow found", title="Result", border_style="yellow"))
    else:
        stream_print(table)
    option = ["Select workflow", "Exit"]
    console.print("Select Command:")
    for i, part_option in enumerate(option):
        console.print(f"{i+1} - {part_option}")
        
    part_choice_idx_str = Prompt.ask(
        "Enter part number",
        choices=[str(i+1) for i in range(len(option))],
        show_choices=False
    )
    if part_choice_idx_str == "2":
        return
    if part_choice_idx_str == "1":
        console.print("\n Select workflow by index to run:")
        choice = Prompt.ask(
            "Enter workflow ID",
            choices=[str(i) for i in range(count)],
            show_choices=True
        )

        workflow = workflow_list[int(choice)]
        workflow_id = workflow["workflow_id"]

    input_messages = []
    if messages:
        for i, msg in enumerate(messages):
            role = "user" if i % 2 == 0 else "assistant"
            input_messages.append({"role": role, "content": msg})
    else:
        input_messages = workflow["user_input_messages"]
    
    request = AgentRequest(
        user_id=user_id,
        lang="en",
        task_type="agent_workflow",
        messages=input_messages,
        debug=False,
        deep_thinking_mode=True,
        search_before_planning=False,
        coor_agents=[],
        workmode="production",
        workflow_id=workflow_id
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
        table.add_column("NickName", style="agent_nick_name")
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
        table.add_column("NickName", style="agent_nick_name")
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
    server: Server = ctx.obj['server']
    stream_print(Panel.fit(f"[highlight]Fetching configuration for {agent_name}...[/highlight]", border_style="cyan"))
    agent: Agent = None
    try:
        async for agent_json in server._list_agents(listAgentRequest(user_id=user_id, match=agent_name)):
            agent = Agent.model_validate_json(agent_json)
            if agent.agent_name == agent_name:
                break
        if not agent:
            stream_print(f"[danger]Agent not found: {agent_name}[/danger]")
            return
    except Exception as e:
        stream_print(f"[danger]Failed to fetch configuration: {str(e)}[/danger]")
        return

    agent_config = agent.model_dump()
    show_agent_config(agent_config)
    modified_config = agent_config.copy()
    stop_editing = False

    if interactive:
        while not stop_editing:
            edit_option_list = ['NickName', 'Description', 'Tool', 'Prompt']
            stop_editing = await edit_agent_option(agent, edit_option_list,agent_config, modified_config,server)


@cli.command(name="run-o")
@click.pass_context
@click.option('--user-id', '-u', required=True, help='User ID')
@click.option('--match', '-m', help='Match string')
@click.option('--interactive/--no-interactive', '-i/-I', default=True, help='Use interactive mode')
@async_command
async def run_polish(ctx, user_id, match, interactive):
    """Edit an existing Workflow interactively"""
    server: Server = ctx.obj['server']
    
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
        option = ["Select workflow", "Exit"]
        console.print("Select Command:")
        for i, part_option in enumerate(option):
            console.print(f"{i+1} - {part_option}")
        part_choice_idx_str = Prompt.ask(
            "Enter part number",
            choices=[str(i+1) for i in range(len(option))],
            show_choices=False
        )
        if part_choice_idx_str == "2":
            break
        if part_choice_idx_str == "1":
            console.print("\n Select workflow by index to polish:")
            choice = Prompt.ask(
                "Enter workflow ID",
                choices=[str(i) for i in range(count)],
                show_choices=True
            )

            workflow = workflow_list[int(choice)]
            workflow_id = workflow["workflow_id"]
            while True:
                parts_to_edit_options = ["graph", "planning_steps","run this workflow","back"]
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
                    agents = workflow_cache.get_editable_agents(workflow_id)

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
                        config = json.loads(json_str)

                    show_agent_config(config)
                    stop_tools_or_prompt = False

                    while not stop_tools_or_prompt:
                        agent_part_options = ["tools", "prompt", "back"]
                        console.print("Select part to edit:")
                        for i, part_option in enumerate(agent_part_options):
                            console.print(f"{i+1} - {part_option}")

                        part_choice_idx_str = Prompt.ask(
                            "Enter part number",
                            choices=[str(i+1) for i in range(len(agent_part_options))],
                            show_choices=False
                        )
                        part_to_edit = agent_part_options[int(part_choice_idx_str) - 1]

                        if part_to_edit == "prompt":
                            while True:
                                polish_prompt_mode = ['AI Assistant','Manually Edit',"back"]
                                console.print("Select mode to edit:")
                                for i, part_option in enumerate(polish_prompt_mode):
                                    console.print(f"{i + 1} - {part_option}")

                                prompt_mode_choice_idx_str = Prompt.ask(
                                    "Enter part number",
                                    choices=[str(i + 1) for i in range(len(polish_prompt_mode))],
                                    show_choices=False
                                )
                                if polish_prompt_mode[int(prompt_mode_choice_idx_str) - 1] == "AI Assistant":
                                    while True:
                                        instruction = Prompt.ask(
                                            "Enter your instruction",
                                            show_default=True
                                        )
                                        polish_content = await polish_agent(_agent=_agent, part_to_edit='prompt', instruction=instruction)
                                        stream_print(f"polished description: \n {polish_content['agent_description']}\n\n")
                                        stream_print(f"polished prompt: \n {polish_content['prompt']}")
                                        while True:
                                            if Confirm.ask("Confirm saving changes?"):
                                                _agent.prompt = polish_content['prompt']
                                                _agent.description = polish_content['agent_description']
                                                try:
                                                    async for result in server._edit_agent(_agent):
                                                        res = json.loads(result)
                                                        if res.get("result") == "success":
                                                            stream_print(Panel.fit("[success]Agent updated successfully![/success]",
                                                                                   border_style="green"))
                                                        else:
                                                            stream_print(
                                                                f"[danger]Update failed: {res.get('result', 'Unknown error')}[/danger]")
                                                except Exception as e:
                                                    stream_print(f"[danger]Error occurred during save: {str(e)}[/danger]")
                                            else:
                                                stream_print("[warning]Modifications cancelled[/warning]")
                                            break
                                        if Confirm.ask("Exit AI Assistant?"):
                                            break
                                if polish_prompt_mode[int(prompt_mode_choice_idx_str) - 1] == "Manually Edit":
                                    modified_config = config.copy()
                                    stop_edit_agent = False
                                    while not stop_edit_agent:
                                        edit_option_list = ['NickName', 'Description', 'Prompt']
                                        stop_edit_agent = await edit_agent_option(_agent,edit_option_list, config, modified_config, server)
                                if polish_prompt_mode[int(prompt_mode_choice_idx_str) - 1] == "back":
                                    break
                        if part_to_edit == "tools":
                            modified_config = config.copy()
                            stop_edit_tool = False
                            while not stop_edit_tool:
                                edit_option_list = ['Tool']
                                stop_edit_tool = await edit_agent_option(_agent,edit_option_list, config, modified_config, server)
                        if part_to_edit == "back":
                            stop_tools_or_prompt = True
                if part_to_edit == "planning_steps":
                    planning = json.loads(workflow.get("planning_steps", ""))
                    steps = planning['steps']
                    planning_steps = [json.dumps(step, indent=2, ensure_ascii=False) for step in steps]
                    table = Table(title=f"Planning steps list for workflow [highlight]{workflow_id}[/highlight]", show_header=True,
                                  header_style="bold magenta", border_style="cyan")
                    table.add_column("Planning steps num", style="tool_desc")
                    table.add_column("content", style="agent_nick_name")
                    for index, step in enumerate(planning_steps):
                        table.add_row(str(index+1),step)
                    stream_print(table)
                    while True:
                        edit_steps_options = ["Select steps num","back"]
                        console.print("Select option:")
                        for i, part_option in enumerate(edit_steps_options):
                            console.print(f"{i + 1} - {part_option}")
                        edit_steps_options_choice = Prompt.ask(
                            "Enter option num",
                            choices=[str(i + 1) for i in range(len(edit_steps_options))],
                            show_choices=True
                        )
                        if edit_steps_options_choice == "1":
                            console.print("\n Select Planning steps by index to polish:")
                            choice = Prompt.ask(
                                "Enter Planning steps num",
                                choices=[str(i+1) for i in range(len(planning_steps))],
                                show_choices=True
                            )
                            editing_step = steps[int(choice) - 1].copy()
                            origin_step = steps[int(choice) - 1]
                            stop_step_edit = False
                            while not stop_step_edit:
                                step_theme = ['Title', 'Description', 'Note', 'Preview', 'Save and Exit ', 'Only Exit']
                                console.print("Select part to edit:")
                                for i, part_option in enumerate(step_theme):
                                    console.print(f"{i + 1} - {part_option}")
                                theme_choice = Prompt.ask(
                                    "Enter part num",
                                    choices=[str(i + 1) for i in range(len(step_theme))],
                                    show_choices=True
                                )
                                if theme_choice == str(1):
                                    new_title = Prompt.ask(
                                        "Enter new title",
                                        default=editing_step.get('title', ''),
                                        show_default=True
                                    )
                                    editing_step['title'] = new_title
                                if theme_choice == str(2):
                                    new_dec = Prompt.ask(
                                        "Enter new description",
                                        default=editing_step.get('description', ''),
                                        show_default=True
                                    )
                                    editing_step['description'] = new_dec
                                if theme_choice == str(3):
                                    new_dec = Prompt.ask(
                                        "Enter new note",
                                        default=editing_step.get('note', ''),
                                        show_default=True
                                    )
                                    editing_step['note'] = new_dec
                                if theme_choice == str(4):
                                    if editing_step == origin_step:
                                        stream_print("No modifications were made!")
                                    else:
                                        stream_print(Panel.fit(
                                            f"[agent_name]Name:[/agent_name] {origin_step.get('agent_name', '')}\n"
                                            f"[step_title]Title:[/step_title] {origin_step.get('title', '')}\n"
                                            f"[step_desc]Description:[/step_desc] {origin_step.get('description', '')}\n"
                                            f"[step_note]Note:[/step_note] {origin_step.get('note', '')}\n",
                                            title="Current Configuration Preview",
                                            border_style="blue"
                                        ))
                                        stream_print(Panel.fit(
                                            f"[agent_name]Name:[/agent_name] {editing_step.get('agent_name', '')}\n"
                                            f"[step_title]Title:[/step_title] {editing_step.get('title', '')}\n"
                                            f"[step_desc]Description:[/step_desc] {editing_step.get('description', '')}\n"
                                            f"[step_note]Note:[/step_note] {editing_step.get('note', '')}\n",
                                            title="Modified Configuration Preview",
                                            border_style="yellow"
                                        ))
                                if theme_choice == str(5):
                                    if Confirm.ask("Confirm saving changes and exit?"):
                                        try:
                                            planning["steps"][int(choice) - 1] = editing_step
                                            step_request = EditStepsRequest(workflow_id=workflow_id, planning_steps=planning)
                                            async for result in server._edit_planning_steps(step_request):
                                                res = json.loads(result)
                                                if res.get("result") == "success":
                                                    stream_print(Panel.fit("[success]Planning Steps updated successfully![/success]",
                                                                           border_style="green"))
                                                else:
                                                    stream_print(
                                                        f"[danger]Update failed: {res.get('result', 'Unknown error')}[/danger]")
                                            stop_step_edit = True
                                        except Exception as e:
                                            stream_print(f"[danger]Error occurred during save: {str(e)}[/danger]")

                                if theme_choice == str(6):
                                    if Confirm.ask("Abandon any changes and exit?"):
                                        stop_step_edit = True
                        else:
                            break
                if part_to_edit == "run this workflow":
                    run_stop = False
                    while not run_stop:
                        pre_user_input_messages = workflow["user_input_messages"]
                        console.print(f"The instruction before this workflow were:\n{pre_user_input_messages}")
                        if Confirm.ask("Do you need to change the instruction for running the workflow this time?"):
                            new_user_input_messages = Prompt.ask(
                                "Enter new instruction: "
                            )
                            _input_messages = [{"role": "user", "content": new_user_input_messages}]
                        else:
                            _input_messages = pre_user_input_messages

                        request = AgentRequest(
                            user_id=user_id,
                            lang="en",
                            task_type="agent_workflow",
                            messages=_input_messages,
                            debug=True,
                            deep_thinking_mode=True,
                            search_before_planning=False,
                            coor_agents=[],
                            workmode="production",
                            workflow_id=workflow_id
                        )

                        console.print(Panel.fit("[highlight]Workflow execution started[/highlight]", title="CoorAgent",
                                                border_style="cyan"))

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
                                    if agent_name:
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
                                        progress.update(task,
                                                        description=f"[agent_name]>>> {agent_name} executing...[/agent_name]")
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
                                    console.print(
                                        Panel.fit("[success]Workflow execution finished![/success]", title="CoorAgent",
                                                  border_style="green"))

                        console.print(Panel.fit("[success]Workflow execution finished![/success]", title="CoorAgent",
                                                border_style="green"))
                        if not Confirm.ask("Do you want to rerun it?"):
                            run_stop = True
                if part_to_edit == "back":
                    break


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


@cli.command(name="evaluate")
@click.pass_context
@click.option('--benchmark', '-b', default="gaia", help='Benchmark to run (default: gaia)')
@click.option('--subset', '-s', default=None, help='Dataset subset or split')
@click.option('--limit', '-l', default=None, type=int, help='Limit number of tasks to run')
@click.option('--max-concurrent', default=5, type=int, help='Max concurrent tasks')
@click.option('--timeout', default=300, type=int, help='Per-task timeout (seconds)')
@async_command
async def evaluate(ctx, benchmark, subset, limit, max_concurrent, timeout):
    """Run benchmark evaluation"""
    from src.evaluation import EvaluationManager
    from src.interface.evaluation import EvaluationConfig

    manager = EvaluationManager()
    config = EvaluationConfig(
        benchmark=benchmark,
        subset=subset,
        limit=limit,
        max_concurrent_tasks=max_concurrent,
        timeout_per_task=timeout,
    )

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"[green]Running evaluation: {benchmark}...", total=None)
        result = await manager.run_evaluation(benchmark, config)
        progress.update(task, description=f"[success]Completed: {benchmark} ({result.num_tasks} tasks)")

    table = Table(title=f"Evaluation Results - {result.benchmark}", show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("Run ID", style="tool_desc")
    table.add_column("Tasks", style="tool_desc")
    table.add_column("Aggregate Score", style="tool_desc")
    table.add_row(result.run_id, str(result.num_tasks), f"{result.metrics.aggregate_score:.3f}")
    stream_print(table)


@cli.command()
def help():
    """Display help information"""
    help_table = Table(title="Help Information", show_header=False, border_style="cyan", width=100)
    help_table.add_column(style="bold cyan")
    help_table.add_column(style="green")
    
    help_table.add_row("[Command] run-l (launch)", "Launch the agent workflow in launch mode")
    help_table.add_row("  -u/--user-id", "User ID (default: test)")
    help_table.add_row("  -t/--task-type", "Task type (required, options: agent_factory, agent_workflow)")
    help_table.add_row("  -m/--message", "Message content (required, use multiple times for multiple messages)")
    help_table.add_row("  --debug/--no-debug", "Enable/disable debug mode (default: disabled)")
    help_table.add_row("  --deep-thinking/--no-deep-thinking", "Enable/disable deep thinking mode (default: enabled)")
    help_table.add_row("  --search-before-planning/--no-search-before-planning", "Enable/disable search before planning (default: disabled)")
    help_table.add_row("  -a/--agents", "List of collaborating Agents (use multiple times to add multiple Agents)")
    help_table.add_row()

    help_table.add_row("[Command] run-p (production)", "Run the agent workflow in production mode")
    help_table.add_row("  -u/--user-id", "User ID (default: test)")
    help_table.add_row("  -m/--message", "Message content (required, use multiple times for multiple messages)")
    help_table.add_row("  -w/--workflow-id", "Workflow ID (optional, if not provided, lists workflows to choose from)")
    help_table.add_row()

    help_table.add_row("[Command] run-o (polish)", "Polish an existing Workflow interactively")
    help_table.add_row("  -u/--user-id", "User ID (required)")
    help_table.add_row("  -m/--match", "Match string for workflows (optional)")
    help_table.add_row("  -i/-I/--interactive/--no-interactive", "Use interactive mode (default: enabled)")
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

    help_table.add_row("[Command] evaluate", "Run benchmark evaluation (e.g., GAIA)")
    help_table.add_row("  -b/--benchmark", "Benchmark name (default: gaia)")
    help_table.add_row("  -s/--subset", "Dataset subset or split")
    help_table.add_row("  -l/--limit", "Limit number of tasks")
    help_table.add_row("  --max-concurrent", "Max concurrent tasks")
    help_table.add_row("  --timeout", "Per-task timeout (seconds)")
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
