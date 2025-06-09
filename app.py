# app.py - Enhanced AI OS with OpenRouter & Together AI Support
import os
import sys
import time
from textwrap import dedent
from datetime import datetime
from typing import Optional
import asyncio
import logging

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter  # <-- NEW: IMPORT OPENROUTER
from agno.models.together import Together      # <-- NEW: IMPORT TOGETHER
from agno.tools.reasoning import ReasoningTools
from agno.tools import tool
from agno.utils.log import logger
from agno.tools.shell import ShellTools
from agno.storage.sqlite import SqliteStorage
import platform
from agno.tools.file import FileTools
from agno.tools.python import PythonTools

system_information = platform.uname()

# Import configuration
try:
    from config import load_config, create_default_config, Config, get_openai_api_key
except ImportError:
    # Fallback if config.py is not available
    Config = None
    load_config = None

# Try to import rich for better terminal UI
DISABLE_RICH = os.environ.get('DISABLE_RICH', '').lower() in ('1', 'true', 'yes')

try:
    if not DISABLE_RICH:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.text import Text
        from rich.status import Status
        from rich.prompt import Prompt, Confirm
        from rich.table import Table
        from rich import print as rprint
        from rich.syntax import Syntax
        RICH_AVAILABLE = True
        console = Console()
    else:
        RICH_AVAILABLE = False
        print("Rich UI disabled by environment variable")
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' library for better UI experience: pip install rich")

# Modern color palette
class ModernColors:
    """Modern, elegant color scheme"""
    # Primary colors
    PRIMARY = '\033[38;2;99;102;241m'      # Indigo
    SECONDARY = '\033[38;2;16;185;129m'    # Emerald  
    ACCENT = '\033[38;2;244;114;182m'      # Pink
    
    # Grays
    GRAY_50 = '\033[38;2;249;250;251m'     # Almost white
    GRAY_400 = '\033[38;2;156;163;175m'    # Medium gray
    GRAY_600 = '\033[38;2;75;85;99m'       # Dark gray
    GRAY_900 = '\033[38;2;17;24;39m'       # Almost black
    
    # Status colors
    SUCCESS = '\033[38;2;34;197;94m'       # Green
    WARNING = '\033[38;2;251;191;36m'      # Amber
    FAIL = '\033[38;2;251;191;36m'         # Amber
    ERROR = '\033[38;2;239;68;68m'         # Red
    INFO = '\033[38;2;59;130;246m'         # Blue
    
    # Special
    GRADIENT_START = '\033[38;2;139;92;246m'  # Purple
    GRADIENT_END = '\033[38;2;59;130;246m'    # Blue
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ENDC = '\033[0m'

class TerminalUI:
    """Modern, minimalist terminal UI wrapper for the agent"""
    
    def __init__(self, agent, config=None):
        self.agent = agent
        self.config = config or load_config()
        self.session_start = datetime.now()
        self.command_history = []
        self.command_count = 0
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_banner(self):
        """Display modern, minimal welcome banner"""
        self.clear_screen()
        
        if RICH_AVAILABLE:
            from rich.align import Align
            from rich.padding import Padding
            
            # Modern minimal banner with enhanced provider support
            banner_content = """
[bold bright_blue]⚡ AI OS[/bold bright_blue] [dim bright_cyan]Enhanced[/dim bright_cyan]
[dim]Multi-Provider Intelligent Terminal Assistant[/dim]

[bright_black]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bright_black]
"""
            
            # System info in clean format
            provider_display = f"[bright_green]{self.config.agent.provider.title()}[/bright_green]"
            if self.config.agent.provider == "openrouter":
                provider_display = f"[bright_magenta]OpenRouter[/bright_magenta]"
            elif self.config.agent.provider == "together":
                provider_display = f"[bright_cyan]Together AI[/bright_cyan]"
            
            system_info = f"""
[dim]System:[/dim] [cyan]{platform.system()} {platform.release()}[/cyan]
[dim]Provider:[/dim] {provider_display}
[dim]Model:[/dim]  [bright_green]{self.config.agent.model}[/bright_green]
[dim]Session:[/dim] [yellow]{self.session_start.strftime('%H:%M')}[/yellow]
"""
            
            console.print(Padding(banner_content, (2, 4)))
            console.print(Padding(system_info, (0, 4)))
            console.print(Padding("[dim]Type [bold]help[/bold] for commands • [bold]exit[/bold] to quit[/dim]", (1, 4)))
            console.print()
            
        else:
            # Fallback minimal design
            print(f"\n{ModernColors.PRIMARY}⚡ AI OS Enhanced{ModernColors.RESET}")
            print(f"{ModernColors.GRAY_400}Multi-Provider Intelligent Terminal Assistant{ModernColors.RESET}")
            print(f"\n{ModernColors.GRAY_600}{'─' * 50}{ModernColors.RESET}")
            print(f"\n{ModernColors.GRAY_400}System:{ModernColors.RESET} {platform.system()} {platform.release()}")
            print(f"{ModernColors.GRAY_400}Provider:{ModernColors.RESET} {self.config.agent.provider.title()}")
            print(f"{ModernColors.GRAY_400}Model:{ModernColors.RESET}  {self.config.agent.model}")
            print(f"{ModernColors.GRAY_400}Session:{ModernColors.RESET} {self.session_start.strftime('%H:%M')}")
            print(f"\n{ModernColors.DIM}Type 'help' for commands • 'exit' to quit{ModernColors.RESET}\n")
    
    def show_help(self):
        """Display modern help information"""
        if RICH_AVAILABLE:
            from rich.columns import Columns
            from rich.padding import Padding
            
            # Commands in clean grid layout
            commands = [
                ("[bold cyan]help[/bold cyan]", "Show this help"),
                ("[bold cyan]clear[/bold cyan]", "Clear screen"),
                ("[bold cyan]history[/bold cyan]", "Command history"),
                ("[bold cyan]stats[/bold cyan]", "Session stats"),
                ("[bold cyan]config[/bold cyan]", "AI Provider settings"),
                ("[bold cyan]models[/bold cyan]", "Available models"),
                ("[bold cyan]export[/bold cyan]", "Export conversation"),
                ("[bold cyan]reset[/bold cyan]", "New session"),
                ("[bold cyan]exit[/bold cyan]", "Quit application"),
            ]
            
            prefixes = [
                ("[bold magenta]![/bold magenta][cyan]cmd[/cyan]", "Execute shell command"),
                ("[bold magenta]?[/bold magenta][cyan]query[/cyan]", "Quick system info"),
            ]
            
            console.print("\n[bold bright_blue]Commands[/bold bright_blue]")
            console.print("[bright_black]━━━━━━━━[/bright_black]\n")
            
            for cmd, desc in commands:
                console.print(f"  {cmd:<20} {desc}")
            
            console.print(f"\n[bold bright_blue]Prefixes[/bold bright_blue]")
            console.print("[bright_black]━━━━━━━━[/bright_black]\n")
            
            for prefix, desc in prefixes:
                console.print(f"  {prefix:<20} {desc}")
            
            console.print(f"\n[dim]Natural language queries supported • 4 AI providers available[/dim]\n")
            
        else:
            print(f"\n{ModernColors.PRIMARY}Commands{ModernColors.RESET}")
            print(f"{ModernColors.GRAY_600}{'─' * 8}{ModernColors.RESET}\n")
            
            commands = [
                ("help", "Show this help"),
                ("clear", "Clear screen"), 
                ("history", "Command history"),
                ("config", "AI Provider settings"),
                ("models", "Available models"),
                ("exit", "Quit application"),
            ]
            
            for cmd, desc in commands:
                print(f"  {ModernColors.SECONDARY}{cmd:<12}{ModernColors.RESET} {desc}")
            
            print(f"\n{ModernColors.DIM}Use natural language for system queries{ModernColors.RESET}\n")
    
    def show_stats(self):
        """Display session statistics in modern format"""
        duration = datetime.now() - self.session_start
        
        if RICH_AVAILABLE:
            from rich.table import Table
            
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Metric", style="dim", justify="right")
            table.add_column("Value", style="bright_cyan")
            
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            
            table.add_row("Duration", duration_str)
            table.add_row("Commands", str(self.command_count))
            table.add_row("Provider", self.config.agent.provider.title())
            table.add_row("Model", self.config.agent.model)
            table.add_row("Started", self.session_start.strftime('%H:%M:%S'))
            
            console.print(f"\n[bold bright_blue]Session Stats[/bold bright_blue]")
            console.print("[bright_black]━━━━━━━━━━━━━[/bright_black]")
            console.print(table)
            console.print()
            
        else:
            print(f"\n{ModernColors.PRIMARY}Session Stats{ModernColors.RESET}")
            print(f"{ModernColors.GRAY_600}{'─' * 13}{ModernColors.RESET}")
            print(f"\n  Duration: {duration}")
            print(f"  Commands: {self.command_count}")
            print(f"  Provider: {self.config.agent.provider.title()}")
            print(f"  Model: {self.config.agent.model}")
            print(f"  Started:  {self.session_start.strftime('%H:%M:%S')}\n")
    
    def show_history(self):
        """Display command history in clean format"""
        if not self.command_history:
            if RICH_AVAILABLE:
                console.print("[dim]No commands in history yet[/dim]\n")
            else:
                print(f"{ModernColors.DIM}No commands in history yet{ModernColors.RESET}\n")
            return
        
        if RICH_AVAILABLE:
            console.print(f"\n[bold bright_blue]Recent Commands[/bold bright_blue]")
            console.print("[bright_black]━━━━━━━━━━━━━━━[/bright_black]\n")
            
            # Show last 10 commands
            recent = self.command_history[-10:]
            for i, (timestamp, cmd) in enumerate(recent, 1):
                cmd_display = cmd[:60] + "..." if len(cmd) > 60 else cmd
                console.print(f"[dim]{timestamp}[/dim] [cyan]{cmd_display}[/cyan]")
            
            if len(self.command_history) > 10:
                console.print(f"\n[dim]... and {len(self.command_history) - 10} more[/dim]")
            console.print()
            
        else:
            print(f"\n{ModernColors.PRIMARY}Recent Commands{ModernColors.RESET}")
            print(f"{ModernColors.GRAY_600}{'─' * 15}{ModernColors.RESET}\n")
            
            recent = self.command_history[-10:]
            for timestamp, cmd in recent:
                print(f"{ModernColors.DIM}{timestamp}{ModernColors.RESET} {cmd}")
            print()
    
    def show_models(self):
        """Display available models for current provider"""
        provider = self.config.agent.provider
    
        if provider in ["openrouter", "together"]:
            # For OpenRouter and Together AI, show input guidance instead of fixed list
            if RICH_AVAILABLE:
                from rich.panel import Panel
                
                if provider == "openrouter":
                    content = """[bold cyan]OpenRouter[/bold cyan] supports 200+ models

    [dim]Popular Examples:[/dim]
    - [cyan]openai/gpt-4o[/cyan] - GPT-4o via OpenRouter
    - [cyan]anthropic/claude-3.5-sonnet[/cyan] - Claude 3.5 Sonnet
    - [cyan]meta-llama/llama-3.1-405b-instruct[/cyan] - Llama 3.1 405B
    - [cyan]mistralai/mixtral-8x7b-instruct[/cyan] - Mixtral 8x7B
    - [cyan]google/gemini-pro-1.5[/cyan] - Gemini Pro 1.5

    [bold]Current Model:[/bold] [yellow]{self.config.agent.model}[/yellow]

    [dim]Full catalog:[/dim] [blue]https://openrouter.ai/models[/blue]"""
        else:
        
            models_by_provider = {
                "openai": [
                    ("gpt-4o", "Latest GPT-4 model, best for complex tasks"),
                    ("gpt-4o-mini", "Faster, cost-effective GPT-4"),
                    ("gpt-3.5-turbo", "Fast and efficient for simpler tasks"),
                    ("o1-preview", "Advanced reasoning model"),
                    ("o1-mini", "Compact reasoning model")
                ],
                "google": [
                    ("gemini-2.0-flash-exp", "Latest experimental Gemini model"),
                    ("gemini-1.5-pro", "Production-ready Gemini Pro"),
                    ("gemini-1.5-flash", "Fast Gemini model")
                ],
                "openrouter": [
                    ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
                    ("meta-llama/llama-3.1-405b-instruct", "Llama 3.1 405B"),
                    ("mistralai/mixtral-8x7b-instruct", "Mixtral 8x7B"),
                    ("google/gemini-pro-1.5", "Gemini Pro 1.5"),
                    ("perplexity/llama-3.1-sonar-large-128k-online", "Perplexity Sonar")
                ],
                "together": [
                    ("meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "Llama 3.1 8B Turbo"),
                    ("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "Llama 3.1 70B Turbo"),
                    ("mistralai/Mixtral-8x7B-Instruct-v0.1", "Mixtral 8x7B"),
                    ("NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO", "Nous Hermes 2"),
                    ("teknium/OpenHermes-2.5-Mistral-7B", "OpenHermes 2.5"),
                    ("togethercomputer/RedPajama-INCITE-7B-Chat", "RedPajama Chat")
                ]
            }
            
            if RICH_AVAILABLE:
                from rich.table import Table
                
                table = Table(title=f"{provider.title()} Available Models", show_header=True, header_style="bold bright_blue")
                table.add_column("Model", style="cyan", min_width=20)
                table.add_column("Description", style="dim")
                table.add_column("Current", style="bright_green", justify="center")
                
                for model_id, description in models_by_provider.get(provider, []):
                    current = "●" if model_id == self.config.agent.model else ""
                    table.add_row(model_id, description, current)
                
                console.print("\n")
                console.print(table)
                console.print("\n[dim]Use 'config' to change provider or model[/dim]\n")
            else:
                print(f"\n{ModernColors.PRIMARY}{provider.title()} Available Models{ModernColors.RESET}")
                print(f"{ModernColors.GRAY_600}{'─' * 30}{ModernColors.RESET}\n")
                
                for model_id, description in models_by_provider.get(provider, []):
                    current = " ●" if model_id == self.config.agent.model else "  "
                    print(f"{current} {ModernColors.SECONDARY}{model_id}{ModernColors.RESET}")
                    print(f"    {ModernColors.DIM}{description}{ModernColors.RESET}")
                print(f"\n{ModernColors.DIM}Use 'config' to change provider or model{ModernColors.RESET}\n")
    
    def show_config_menu(self):
        """Enhanced configuration interface with all providers"""
        from config import load_config, save_config
        
        config = load_config()
        
        while True:
            self.clear_screen()
            
            if RICH_AVAILABLE:
                console.print(f"\n[bold bright_blue]⚙️  AI Configuration[/bold bright_blue]")
                console.print("[bright_black]━━━━━━━━━━━━━━━━━━━━━[/bright_black]\n")
                
                # AI Settings
                provider_display = config.agent.provider.title()
                if config.agent.provider == "openrouter":
                    provider_display = "[magenta]OpenRouter[/magenta]"
                elif config.agent.provider == "together":
                    provider_display = "[cyan]Together AI[/cyan]"
                elif config.agent.provider == "google":
                    provider_display = "[bright_blue]Google[/bright_blue]"
                elif config.agent.provider == "openai":
                    provider_display = "[bright_green]OpenAI[/bright_green]"
                
                console.print("[bold bright_green]AI Provider & Model[/bold bright_green]")
                console.print(f"[dim]1.[/dim] Provider     {provider_display}")
                console.print(f"[dim]2.[/dim] Model        [cyan]{config.agent.model}[/cyan]")
                console.print(f"[dim]3.[/dim] Temperature  [cyan]{config.agent.temperature}[/cyan]")
                console.print(f"[dim]4.[/dim] Max Tokens   [cyan]{config.agent.max_tokens}[/cyan]")
                
                # API Keys
                console.print(f"\n[bold bright_green]API Keys[/bold bright_green]")
                openai_key_display = "••••" + config.agent.openai_api_key[-4:] if config.agent.openai_api_key else "[dim]Not set[/dim]"
                google_key_display = "••••" + config.agent.google_api_key[-4:] if config.agent.google_api_key else "[dim]Not set[/dim]"
                openrouter_key_display = "••••" + config.agent.openrouter_api_key[-4:] if hasattr(config.agent, 'openrouter_api_key') and config.agent.openrouter_api_key else "[dim]Not set[/dim]"
                together_key_display = "••••" + config.agent.together_api_key[-4:] if hasattr(config.agent, 'together_api_key') and config.agent.together_api_key else "[dim]Not set[/dim]"
                
                console.print(f"[dim]5.[/dim] OpenAI       {openai_key_display}")
                console.print(f"[dim]6.[/dim] Google       {google_key_display}")
                console.print(f"[dim]7.[/dim] OpenRouter   {openrouter_key_display}")
                console.print(f"[dim]8.[/dim] Together AI  {together_key_display}")
                
                # UI Settings  
                console.print(f"\n[bold bright_green]Interface[/bold bright_green]")
                console.print(f"[dim]9.[/dim]  Tool Calls  [cyan]{'On' if config.ui.show_tool_calls else 'Off'}[/cyan]")
                console.print(f"[dim]10.[/dim] Markdown    [cyan]{'On' if config.ui.markdown else 'Off'}[/cyan]")
                
                console.print(f"\n[dim]Enter number to modify • [bold]save[/bold] to apply • [bold]exit[/bold] to cancel[/dim]\n")
                
            else:
                print(f"\n{ModernColors.PRIMARY}⚙️  AI Configuration{ModernColors.RESET}")
                print(f"{ModernColors.GRAY_600}{'─' * 21}{ModernColors.RESET}\n")
                print("1. Provider:", config.agent.provider.title())
                print("2. Model:", config.agent.model)
                print("3. Temperature:", config.agent.temperature)
                print("4. Max Tokens:", config.agent.max_tokens)
                print("\nEnter number to change, 'save' to apply, 'exit' to cancel\n")
            
            choice = input("→ ").strip().lower()
            
            if choice == 'exit':
                return
            elif choice == 'save':
                if save_config(config):
                    if RICH_AVAILABLE:
                        console.print("[bright_green]✓[/bright_green] [green]Configuration saved[/green]")
                        console.print("[dim]Restart required for changes to take effect[/dim]")
                    else:
                        print(f"{ModernColors.SUCCESS}✓ Configuration saved{ModernColors.RESET}")
                    time.sleep(2)
                    return
                else:
                    if RICH_AVAILABLE:
                        console.print("[red]✗ Error saving configuration[/red]")
                    else:
                        print(f"{ModernColors.ERROR}✗ Error saving configuration{ModernColors.RESET}")
                    time.sleep(1.5)
            
            elif choice.isdigit():
                option = int(choice)
                
                if option == 1:  # Provider
                    providers = ["openai", "google", "openrouter", "together"]
                    if RICH_AVAILABLE:
                        console.print("\n[bold]Select AI Provider[/bold]")
                        for i, p in enumerate(providers):
                            marker = "●" if p == config.agent.provider else "○"
                            display_name = p.title()
                            if p == "openrouter":
                                display_name = "OpenRouter"
                            elif p == "together":
                                display_name = "Together AI"
                            console.print(f"  {i+1}. {marker} {display_name}")
                        choice = Prompt.ask("Choice", default="1")
                    else:
                        print("\nSelect AI Provider:")
                        for i, p in enumerate(providers):
                            print(f"  {i+1}. {p.title()}")
                        choice = input("Choice [1]: ") or "1"
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(providers):
                        new_provider = providers[int(choice)-1]
                        if new_provider != config.agent.provider:
                            config.agent.provider = new_provider
                            # Auto-set appropriate default model
                            if new_provider == "openai":
                                config.agent.model = "gpt-4o-mini"
                            elif new_provider == "google":
                                config.agent.model = "gemini-2.0-flash-exp"
                            elif new_provider == "openrouter":
                                config.agent.model = "openai/gpt-4o"
                            elif new_provider == "together":
                                config.agent.model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
                
                elif option == 2:  # Model
                    if config.agent.provider in ["openrouter", "together"]:
                        # For OpenRouter and Together AI, allow direct model input
                        if RICH_AVAILABLE:
                            if config.agent.provider == "openrouter":
                                console.print(f"\n[bold]Enter OpenRouter Model[/bold]")
                                console.print("[dim]Examples:[/dim]")
                                console.print("  [cyan]openai/gpt-4o[/cyan]")
                                console.print("  [cyan]anthropic/claude-3.5-sonnet[/cyan]")
                                console.print("  [cyan]meta-llama/llama-3.1-405b-instruct[/cyan]")
                                console.print("  [cyan]mistralai/mixtral-8x7b-instruct[/cyan]")
                                console.print(f"\n[dim]Current:[/dim] [yellow]{config.agent.model}[/yellow]")
                                console.print("[dim]See all models at:[/dim] [blue]https://openrouter.ai/models[/blue]")
                                new_model = Prompt.ask("Model name", default=config.agent.model)
                            else:  # together
                                console.print(f"\n[bold]Enter Together AI Model[/bold]")
                                console.print("[dim]Examples:[/dim]")
                                console.print("  [cyan]meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo[/cyan]")
                                console.print("  [cyan]meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo[/cyan]")
                                console.print("  [cyan]mistralai/Mixtral-8x7B-Instruct-v0.1[/cyan]")
                                console.print("  [cyan]NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO[/cyan]")
                                console.print(f"\n[dim]Current:[/dim] [yellow]{config.agent.model}[/yellow]")
                                console.print("[dim]See all models at:[/dim] [blue]https://api.together.xyz/models[/blue]")
                                new_model = Prompt.ask("Model name", default=config.agent.model)
                        else:
                            if config.agent.provider == "openrouter":
                                print(f"\nEnter OpenRouter Model:")
                                print("Examples: openai/gpt-4o, anthropic/claude-3.5-sonnet")
                                print(f"Current: {config.agent.model}")
                                print("See all models at: https://openrouter.ai/models")
                            else:  # together
                                print(f"\nEnter Together AI Model:")
                                print("Examples: meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo")
                                print(f"Current: {config.agent.model}")
                                print("See all models at: https://api.together.xyz/models")
                            new_model = input(f"Model name [{config.agent.model}]: ").strip()
                            if not new_model:
                                new_model = config.agent.model
                        
                        if new_model and new_model != config.agent.model:
                            config.agent.model = new_model
                            if RICH_AVAILABLE:
                                console.print(f"[bright_green]✓[/bright_green] Model updated to: [cyan]{new_model}[/cyan]")
                            else:
                                print(f"✓ Model updated to: {new_model}")
                    else:
                        models_by_provider = {
                            "openai": ["gpt-4.1", "gpt-4o-mini", "gpt-4o", "o3-mini", "o3", "o1-mini", "o1", "o1-pro"],
                            "google": ["gemini-2.5-flash-preview-05-06", "gemini-2.5-pro-preview-06-05"],
                            "openrouter": [
                                "openai/gpt-4.1", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-405b-instruct",
                                "mistralai/mixtral-8x7b-instruct", "google/gemini-pro-1.5"
                            ],
                            "together": [
                                "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                                "mistralai/Mixtral-8x7B-Instruct-v0.1", "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"
                            ]
                        }
                    
                        models = models_by_provider.get(config.agent.provider, [])
                        
                        if RICH_AVAILABLE:
                            console.print(f"\n[bold]Select {config.agent.provider.title()} Model[/bold]")
                            for i, m in enumerate(models):
                                marker = "●" if m == config.agent.model else "○"
                                console.print(f"  {i+1}. {marker} {m}")
                            choice = Prompt.ask("Choice", default="1")
                        else:
                            print(f"\nSelect {config.agent.provider.title()} Model:")
                            for i, m in enumerate(models):
                                print(f"  {i+1}. {m}")
                            choice = input("Choice [1]: ") or "1"
                        
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            config.agent.model = models[int(choice)-1]
                
                elif option == 3:  # Temperature
                    config.agent.temperature = self._get_float("Temperature (0.0-1.0): ", config.agent.temperature)
                elif option == 4:  # Max tokens
                    config.agent.max_tokens = self._get_int("Max tokens: ", config.agent.max_tokens)
                elif option == 5:  # OpenAI API key
                    config.agent.openai_api_key = self._get_password("OpenAI API key: ")
                elif option == 6:  # Google API key
                    config.agent.google_api_key = self._get_password("Google API key: ")
                elif option == 7:  # OpenRouter API key
                    if not hasattr(config.agent, 'openrouter_api_key'):
                        config.agent.openrouter_api_key = ""
                    config.agent.openrouter_api_key = self._get_password("OpenRouter API key: ")
                elif option == 8:  # Together API key
                    if not hasattr(config.agent, 'together_api_key'):
                        config.agent.together_api_key = ""
                    config.agent.together_api_key = self._get_password("Together AI API key: ")
                elif option == 9:  # Tool calls
                    config.ui.show_tool_calls = self._get_boolean("Show tool calls? ", config.ui.show_tool_calls)
                elif option == 10:  # Markdown
                    config.ui.markdown = self._get_boolean("Enable markdown? ", config.ui.markdown)
    
    def get_user_input(self) -> str:
        """Get input with modern prompt style"""
        if RICH_AVAILABLE:
            return Prompt.ask(f"[bold bright_blue]▶[/bold bright_blue]")
        else:
            return input(f"{ModernColors.PRIMARY}▶{ModernColors.RESET} ")
    
    def export_conversation(self):
        """Export with modern feedback"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        filename = os.path.join(export_dir, f"session_{timestamp}.md")
        
        try:
            with open(filename, 'w') as f:
                f.write(f"# AI OS Enhanced Session Export\n")
                f.write(f"**Date:** {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Provider:** {self.config.agent.provider.title()}\n")
                f.write(f"**Model:** {self.config.agent.model}\n\n")
                f.write("## Commands\n\n")
                for timestamp, cmd in self.command_history:
                    f.write(f"**{timestamp}** → `{cmd}`\n\n")
            
            if RICH_AVAILABLE:
                console.print(f"[bright_green]✓[/bright_green] [green]Exported to[/green] [cyan]{filename}[/cyan]")
            else:
                print(f"{ModernColors.SUCCESS}✓ Exported to {filename}{ModernColors.RESET}")
                
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]✗ Export failed: {str(e)}[/red]")
            else:
                print(f"{ModernColors.ERROR}✗ Export failed: {str(e)}{ModernColors.RESET}")
    
    def run(self):
        """Main run loop with modern styling"""
        self.show_banner()
        
        while True:
            try:
                user_input = self.get_user_input().strip()
                
                if not user_input:
                    continue
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.command_history.append((timestamp, user_input))
                self.command_count += 1
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    if RICH_AVAILABLE:
                        if Confirm.ask("\n[yellow]Exit AI OS?[/yellow]"):
                            console.print("\n[bright_blue]👋 See you later![/bright_blue]\n")
                            break
                    else:
                        confirm = input(f"\n{ModernColors.WARNING}Exit AI OS? (y/n): {ModernColors.RESET}")
                        if confirm.lower() == 'y':
                            print(f"\n{ModernColors.PRIMARY}👋 See you later!{ModernColors.RESET}\n")
                            break
                    continue
                
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'config':
                    self.show_config_menu()
                    continue
                elif user_input.lower() == 'models':
                    self.show_models()
                    continue
                elif user_input.lower() == 'clear':
                    self.clear_screen()
                    continue
                elif user_input.lower() == 'history':
                    self.show_history()
                    continue
                elif user_input.lower() == 'stats':
                    self.show_stats()
                    continue
                elif user_input.lower() == 'export':
                    self.export_conversation()
                    continue
                elif user_input.lower() == 'reset':
                    if RICH_AVAILABLE and Confirm.ask("[yellow]Start new session?[/yellow]"):
                        self.command_history.clear()
                        self.command_count = 0
                        self.session_start = datetime.now()
                        self.show_banner()
                    continue
                
                # Process special prefixes
                processed_input = self.process_special_command(user_input)
                if processed_input:
                    user_input = processed_input
                
                # Show thinking indicator
                if RICH_AVAILABLE:
                    with console.status("[dim]processing...[/dim]", spinner="dots"):
                        time.sleep(0.1)
                
                print()
                self.agent.print_response(user_input)
                print()
                
            except KeyboardInterrupt:
                if RICH_AVAILABLE:
                    console.print(f"\n[dim]Use [bold]exit[/bold] to quit properly[/dim]")
                else:
                    print(f"\n{ModernColors.DIM}Use 'exit' to quit properly{ModernColors.RESET}")
                continue
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(f"[red]✗ {str(e)}[/red]")
                else:
                    print(f"{ModernColors.ERROR}✗ {str(e)}{ModernColors.RESET}")
                logger.error(f"Error: {e}", exc_info=True)
    
    # Helper methods with modern styling
    def _get_float(self, prompt, default=0.0):
        while True:
            try:
                if RICH_AVAILABLE:
                    user_input = Prompt.ask(prompt, default=str(default))
                else:
                    user_input = input(f"{prompt} [{default}]: ")
                    if not user_input:
                        return default
                return float(user_input)
            except ValueError:
                if RICH_AVAILABLE:
                    console.print("[red]Please enter a valid number[/red]")
                else:
                    print(f"{ModernColors.ERROR}Please enter a valid number{ModernColors.RESET}")
    
    def _get_int(self, prompt, default=0):
        while True:
            try:
                if RICH_AVAILABLE:
                    user_input = Prompt.ask(prompt, default=str(default))
                else:
                    user_input = input(f"{prompt} [{default}]: ")
                    if not user_input:
                        return default
                return int(user_input)
            except ValueError:
                if RICH_AVAILABLE:
                    console.print("[red]Please enter a valid number[/red]")
                else:
                    print(f"{ModernColors.ERROR}Please enter a valid number{ModernColors.RESET}")
    
    def _get_password(self, prompt):
        import getpass
        try:
            return getpass.getpass(prompt)
        except:
            if RICH_AVAILABLE:
                return Prompt.ask(prompt, password=True)
            else:
                return input(f"{prompt} (visible): ")
    
    def _get_boolean(self, prompt, default=False):
        if RICH_AVAILABLE:
            return Confirm.ask(prompt, default=default)
        else:
            default_display = "Y/n" if default else "y/N"
            user_input = input(f"{prompt} [{default_display}]: ").strip().lower()
            if not user_input:
                return default
            return user_input.startswith('y')
    
    def process_special_command(self, user_input: str) -> Optional[str]:
        """Process special commands and prefixes"""
        if user_input.startswith('!'):
            shell_cmd = user_input[1:].strip()
            return f"Execute this shell command and show the results: {shell_cmd}"
        elif user_input.startswith('?'):
            query = user_input[1:].strip()
            return f"Quick system check: {query}"
        return None

def main():
    """Enhanced main entry point with multi-provider support"""
    get_openai_api_key()
    Colors = ModernColors
    try:
        config = None
        if load_config:
            config = load_config()
            
            os.makedirs(os.path.dirname(config.logging.file), exist_ok=True)
            logging.basicConfig(
                level=getattr(logging, config.logging.level.upper(), logging.INFO),
                format=config.logging.format,
                handlers=[
                    logging.FileHandler(config.logging.file),
                    logging.StreamHandler()
                ]
            )
        
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("exports", exist_ok=True)
        
        # ======== ENHANCED DYNAMIC MODEL INITIALIZATION ========
        model_instance = None
        agent_config = config.agent

        if agent_config.provider == "openai":
            api_key = agent_config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: OpenAI API key not found in config or OPENAI_API_KEY environment variable." + Colors.ENDC)
                print("Please run 'python app.py', enter 'config', and set your key.")
                sys.exit(1)
            model_instance = OpenAIChat(
                id=agent_config.model,
                api_key=api_key,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens
            )
            
        elif agent_config.provider == "google":
            api_key = agent_config.google_api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: Google API key not found in config or GOOGLE_API_KEY environment variable." + Colors.ENDC)
                print("Please run 'python app.py', enter 'config', and set your key.")
                sys.exit(1)
            model_instance = Gemini(
                id=agent_config.model,
                api_key=api_key,
                temperature=agent_config.temperature,
            )
            
        elif agent_config.provider == "openrouter":
            api_key = getattr(agent_config, 'openrouter_api_key', None) or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: OpenRouter API key not found in config or OPENROUTER_API_KEY environment variable." + Colors.ENDC)
                print("Please run 'python app.py', enter 'config', and set your key.")
                print("Get your API key from: https://openrouter.ai/keys")
                sys.exit(1)
            model_instance = OpenRouter(
                id=agent_config.model,
                api_key=api_key,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens
            )
            
        elif agent_config.provider == "together":
            api_key = getattr(agent_config, 'together_api_key', None) or os.getenv("TOGETHER_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: Together AI API key not found in config or TOGETHER_API_KEY environment variable." + Colors.ENDC)
                print("Please run 'python app.py', enter 'config', and set your key.")
                print("Get your API key from: https://api.together.xyz/settings/api-keys")
                sys.exit(1)
            model_instance = Together(
                id=agent_config.model,
                api_key=api_key,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens
            )
            
        else:
            print(f"{Colors.FAIL}Error: Unknown AI provider '{agent_config.provider}' in configuration.{Colors.ENDC}")
            print("Supported providers: openai, google, openrouter, together")
            sys.exit(1)
        
        # ===============================================

        reasoning_agent = Agent(
            model=model_instance,
            tools=[ReasoningTools(add_instructions=True), ShellTools(), FileTools(), PythonTools()],
            instructions=dedent(f"""\
                system_information = {system_information}
                
                You are an expert System Intelligence Terminal Assistant with strong analytical, system administration, and IoT skills! 🧠
                
                Current AI Configuration:
                - Provider: {agent_config.provider.title()}
                - Model: {agent_config.model}
                - You have access to multiple AI providers (OpenAI, Google, OpenRouter, Together AI)
                
                You are running on the user's system and have full access to analyze and manage it through shell commands. 
                You will also be given IoT devices connected to the system to manage.
                Your role is to:
                1. Understand user queries and plan and execute commands appropriate for the current system and environment.
                2. Analyze command outputs intelligently
                3. Provide clear, actionable insights
                4. Help with system administration, monitoring, and automation
                5. Leverage the capabilities of your current AI model provider
                
                Always:
                - Understand what is the current system you are working on.
                - Be concise but thorough
                - Explain technical concepts clearly
                - Suggest follow-up actions when relevant
                - Warn about potentially dangerous operations. Only move ahead if the user explicitly confirms for it.
                - Mention your current AI provider capabilities when relevant

                Note:
                - If the user asks for something which requires external connections(for eg, fetching emails from a service), come up with a plan (that can be executed from the terminal) and ask for confirmation.
                - Once the user confirms, execute the plan. Ask for more details required from the user's end if needed.
                - When user asks for something which requires saving data to files, name the file in a way that it is searchable and easy to understand. keep them into folder with date.
                - If the execution output of a command is very large, save the output to a file or write a script to process the output.
                - You can suggest switching AI providers if a task would benefit from a different model's strengths.
                
                Format your responses with clear sections and use markdown for readability, colors to denote urgency and priority.
            """),
            add_datetime_to_instructions=True,
            stream_intermediate_steps=config.ui.show_tool_calls,
            show_tool_calls=config.ui.show_tool_calls,
            markdown=config.ui.markdown,
            storage=SqliteStorage(
                table_name="sita_agent_sessions", 
                db_file=config.storage.db_file
            ),
            add_history_to_messages=True,
            num_history_runs=3,
        )
        
        ui = TerminalUI(reasoning_agent, config)
        ui.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        error_msg = f"\n{Colors.FAIL}Fatal error: {e}{Colors.ENDC}"
        if RICH_AVAILABLE:
            console.print(f"[red]Fatal error: {e}[/red]")
        else:
            print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()