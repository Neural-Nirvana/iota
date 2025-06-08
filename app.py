# main.py
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
from agno.models.google import Gemini  # <-- IMPORT GEMINI
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
    from config import load_config, create_default_config, Config
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

# Color codes for terminal if rich is not available
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class TerminalUI:
    """Enhanced terminal UI wrapper for the agent"""
    
    def __init__(self, agent, config=None):
        self.agent = agent
        self.config = config
        self.session_start = datetime.now()
        self.command_history = []
        self.command_count = 0
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_banner(self):
        """Display welcome banner"""
        self.clear_screen()
        
        banner = """
    ██████████████████████████████████████████████████
    ██                                              ██
    ██    ┌─────┐  ████████ ██  ██ ████████         ██
    ██    │ ◉ ◉ │    ██     ██  ██ ██               ██
    ██    │  >  │    ██     ██████ ████             ██
    ██    └─────┘    ██     ██  ██ ██               ██
    ██               ██     ██  ██ ████████         ██
    ██                                              ██
    ██      █████╗ ██╗       ██████╗ ███████╗       ██
    ██     ██╔══██╗██║      ██╔═══██╗██╔════╝       ██
    ██     ███████║██║      ██║   ██║███████╗       ██
    ██     ██╔══██║██║      ██║   ██║╚════██║       ██
    ██     ██║  ██║██║      ╚██████╔╝███████║       ██
    ██     ╚═╝  ╚═╝╚═╝       ╚═════╝ ╚══════╝       ██
    ██                                              ██
    ██    ╔═══════════════════════════════════════╗ ██
    ██    ║ For Tinkerers and Builders            ║ ██
    ██    ╚═══════════════════════════════════════╝ ██
    ██                                              ██
    ██████████████████████████████████████████████████
        """
        
        if RICH_AVAILABLE:
            console.print(Panel(banner, style="bold cyan"))
            console.print(platform.machine()+', '+ platform.processor()+', '+ platform.release()+', '+ platform.version())
            console.print("[dim]Type 'help' for commands, 'exit' to quit[/dim]\n")
        else:
            print(Colors.CYAN + banner + Colors.ENDC)
            print(platform.uname())
            print(Colors.BLUE + "Type 'help' for commands, 'exit' to quit\n" + Colors.ENDC)
    
    def show_help(self):
        """Display help information"""
        help_text = """
Available Commands:
• help       - Show this help message
• clear      - Clear the screen
• history    - Show command history
• stats      - Show session statistics
• export     - Export conversation to file
• config     - Configure application settings
• reset      - Start a new session
• exit/quit  - Exit the application

Special Prefixes:
• !<command> - Execute shell command directly
• ?<query>   - Quick system info query

Tips:
• Ask about system configuration, processes, network, files, etc.
• The assistant can execute commands and analyze results
• Use natural language for complex queries
        """
        
        if RICH_AVAILABLE:
            console.print(Panel(help_text, title="Help", style="green"))
        else:
            print(Colors.GREEN + "=== HELP ===" + Colors.ENDC)
            print(help_text)
    
    def show_stats(self):
        """Display session statistics"""
        duration = datetime.now() - self.session_start
        stats = f"""
Session Statistics:
• Session Duration: {duration}
• Commands Executed: {self.command_count}
• Session Started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if RICH_AVAILABLE:
            table = Table(title="Session Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Session Duration", str(duration))
            table.add_row("Commands Executed", str(self.command_count))
            table.add_row("Session Started", self.session_start.strftime('%Y-%m-%d %H:%M:%S'))
            console.print(table)
        else:
            print(Colors.CYAN + stats + Colors.ENDC)
    
    def show_history(self):
        """Display command history"""
        if not self.command_history:
            print("No commands in history yet.")
            return
        
        if RICH_AVAILABLE:
            table = Table(title="Command History")
            table.add_column("#", style="dim", width=4)
            table.add_column("Time", style="cyan")
            table.add_column("Command", style="white")
            
            for i, (timestamp, cmd) in enumerate(self.command_history, 1):
                table.add_row(str(i), timestamp, cmd[:60] + "..." if len(cmd) > 60 else cmd)
            
            console.print(table)
        else:
            print(Colors.BOLD + "Command History:" + Colors.ENDC)
            for i, (timestamp, cmd) in enumerate(self.command_history, 1):
                print(f"{i}. [{timestamp}] {cmd}")
    
    def export_conversation(self):
        """Export conversation to a file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Use configured export directory or default
        export_dir = "exports"
        if self.config and hasattr(self.config.storage, 'export_dir'):
            export_dir = self.config.storage.export_dir
        
        os.makedirs(export_dir, exist_ok=True)
        filename = os.path.join(export_dir, f"conversation_{timestamp}.md")
        
        try:
            # BUG: This is a placeholder. A real implementation would query the agent's
            # storage (e.g., the SQLite DB) to get the full conversation.
            with open(filename, 'w') as f:
                f.write(f"# System Intelligence Terminal Assistant\n")
                f.write(f"## Session: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("### Command History\n\n")
                for timestamp, cmd in self.command_history:
                    f.write(f"**[{timestamp}]** {cmd}\n\n")
            
            success_msg = f"Conversation exported to: {filename}"
            if RICH_AVAILABLE:
                console.print(f"[green]✓[/green] {success_msg}")
            else:
                print(Colors.GREEN + "✓ " + success_msg + Colors.ENDC)
        except Exception as e:
            error_msg = f"Failed to export: {str(e)}"
            if RICH_AVAILABLE:
                console.print(f"[red]✗[/red] {error_msg}")
            else:
                print(Colors.FAIL + "✗ " + error_msg + Colors.ENDC)
    
    def process_special_command(self, user_input: str) -> Optional[str]:
        """Process special commands and prefixes"""
        if user_input.startswith('!'):
            shell_cmd = user_input[1:].strip()
            return f"Execute this shell command and show the results: {shell_cmd}"
        
        elif user_input.startswith('?'):
            query = user_input[1:].strip()
            return f"Quick system check: {query}"
        
        return None
    
    def get_user_input(self) -> str:
        """Get input from user with enhanced prompt"""
        if RICH_AVAILABLE:
            prompt_text = f"[bold cyan]agent[{self.command_count + 1}][/bold cyan]> "
            return Prompt.ask(prompt_text)
        else:
            return input(f"{Colors.CYAN}agent[{self.command_count + 1}]>{Colors.ENDC} ")
    
    def display_thinking(self):
        """Show thinking indicator"""
        if not RICH_AVAILABLE:
            print(Colors.BLUE + "🤔 Thinking..." + Colors.ENDC)

    def show_config_menu(self):
        """Display and manage configuration settings"""
        from config import load_config, save_config, Config, NetworkConfig, AgentConfig
        
        config = load_config()
        
        while True:
            self.clear_screen()
            
            if RICH_AVAILABLE:
                console.print(Panel("[bold cyan]Configuration Menu[/bold cyan]"))
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim", width=3)
                table.add_column("Setting", style="bold")
                table.add_column("Value", style="cyan")
                
                table.add_row("", "[yellow bold]Agent Settings[/yellow bold]", "")
                table.add_row("1", "AI Provider", config.agent.provider.capitalize())
                table.add_row("2", "Model", config.agent.model)
                table.add_row("3", "Temperature", str(config.agent.temperature))
                table.add_row("4", "Max Tokens", str(config.agent.max_tokens))
                table.add_row("5", "Set OpenAI API Key", "****" + config.agent.openai_api_key[-4:] if config.agent.openai_api_key else "[italic](Not set)[/italic]")
                table.add_row("6", "Set Google API Key", "****" + config.agent.google_api_key[-4:] if config.agent.google_api_key else "[italic](Not set)[/italic]")

                table.add_row("", "[yellow bold]UI Settings[/yellow bold]", "")
                table.add_row("7", "Show Tool Calls", str(config.ui.show_tool_calls))
                table.add_row("8", "Enable Markdown", str(config.ui.markdown))

                console.print(table)
                console.print("\n[dim]Enter setting number to change, 'save' to apply, or 'exit' to discard changes.[/dim]")
            else:
                print(Colors.HEADER + "Configuration Menu" + Colors.ENDC + "\n")
                # Simplified non-rich version
                print("1. AI Provider: ", config.agent.provider.capitalize())
                print("2. Model: ", config.agent.model)
                # ... and so on
                print("\nEnter setting number to change, or 'save' to save and exit, or 'exit' to exit without saving")

            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == 'exit':
                return
            elif choice == 'save':
                if save_config(config):
                    if RICH_AVAILABLE:
                        console.print("[green]Configuration saved successfully! Please restart the application for all changes to take effect.[/green]")
                    else:
                        print(Colors.GREEN + "Configuration saved successfully! Please restart the application." + Colors.ENDC)
                    time.sleep(2)
                    return
                else:
                    if RICH_AVAILABLE:
                        console.print("[red]Error saving configuration[/red]")
                    else:
                        print(Colors.FAIL + "Error saving configuration" + Colors.ENDC)
                    time.sleep(1.5)
            elif choice.isdigit():
                option = int(choice)
                
                # Agent settings
                if option == 1: # AI Provider
                    providers = ["openai", "google"]
                    current_provider_index = providers.index(config.agent.provider) if config.agent.provider in providers else 0
                    choice = self._get_choice("Select AI Provider", providers, default=str(current_provider_index + 1))
                    if choice.isdigit() and 1 <= int(choice) <= len(providers):
                        new_provider = providers[int(choice)-1]
                        if new_provider != config.agent.provider:
                            config.agent.provider = new_provider
                            # Reset model to a default for the new provider
                            if new_provider == "openai":
                                config.agent.model = "gpt-4o-mini"
                            elif new_provider == "google":
                                config.agent.model = "gemini-2.5-flash-preview-04-17"
                            console.print(f"[yellow]Provider changed to '{new_provider}'. Model reset to '{config.agent.model}'.[/yellow]")
                            time.sleep(1.5)

                elif option == 2: # Model
                    if config.agent.provider == "openai":
                        models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-3.5-turbo"]
                    elif config.agent.provider == "google":
                        models = ["gemini-2.5-flash-preview-04-17", "gemini-2.5-pro"]
                    else:
                        console.print("[red]Unknown provider configured. Cannot select model.[/red]")
                        time.sleep(1.5)
                        continue
                    
                    default_index = models.index(config.agent.model) + 1 if config.agent.model in models else 1
                    choice = self._get_choice(f"Select a {config.agent.provider.capitalize()} model", models, default=str(default_index))
                    if choice.isdigit() and 1 <= int(choice) <= len(models):
                        config.agent.model = models[int(choice)-1]

                elif option == 3:
                    config.agent.temperature = self._get_float("Enter Temperature (0.0-1.0): ", config.agent.temperature)
                elif option == 4:
                    config.agent.max_tokens = self._get_int("Enter Max Tokens: ", config.agent.max_tokens)
                elif option == 5:
                    config.agent.openai_api_key = self._get_password("Enter OpenAI API Key: ")
                elif option == 6:
                    config.agent.google_api_key = self._get_password("Enter Google API Key: ")
                
                # UI settings
                elif option == 7:
                    config.ui.show_tool_calls = self._get_boolean("Show Tool Calls? (y/n): ", config.ui.show_tool_calls)
                elif option == 8:
                    config.ui.markdown = self._get_boolean("Enable Markdown? (y/n): ", config.ui.markdown)
    
    def _get_choice(self, prompt, options, default="1"):
        """Helper to get a choice from a list."""
        if RICH_AVAILABLE:
            console.print(f"\n[bold]{prompt}[/bold]")
            for i, option in enumerate(options):
                console.print(f"  {i+1}. {option}")
            return Prompt.ask("Select an option", default=default)
        else:
            print(f"\n{prompt}")
            for i, option in enumerate(options):
                print(f"  {i+1}. {option}")
            return input(f"Select an option [{default}]: ") or default

    def _get_input(self, prompt, default=None):
        """Get user input with optional default value"""
        if RICH_AVAILABLE:
            return Prompt.ask(prompt, default=default or "")
        else:
            default_display = f" [{default}]" if default else ""
            user_input = input(f"{prompt}{default_display}: ")
            return user_input if user_input.strip() else default
    
    def _get_password(self, prompt):
        """Get password input without echo"""
        import getpass
        try:
            return getpass.getpass(prompt)
        except:
            if RICH_AVAILABLE:
                return Prompt.ask(prompt, password=True)
            else:
                return input(f"{prompt} (note: input will be visible): ")
    
    def _get_boolean(self, prompt, default=False):
        """Get boolean input"""
        if RICH_AVAILABLE:
            return Confirm.ask(prompt, default=default)
        else:
            default_display = "Y/n" if default else "y/N"
            user_input = input(f"{prompt} [{default_display}]: ").strip().lower()
            if not user_input:
                return default
            return user_input.startswith('y')
    
    def _get_int(self, prompt, default=0):
        """Get integer input"""
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
                    print(Colors.FAIL + "Please enter a valid number" + Colors.ENDC)
    
    def _get_float(self, prompt, default=0.0):
        """Get float input"""
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
                    print(Colors.FAIL + "Please enter a valid number" + Colors.ENDC)
    
    def run(self):
        """Main run loop with enhanced UI"""
        self.show_banner()
        exit_banner = """
        
    ████████████████████████████████████████████████████████
    █                                                      █
    █     ┌─────┐    ╔══════════════════════════════════╗  █
    █     │ ◉ ◉ │    ║                                  ║  █
    █     │  ∩  │ ~  ║  Thanks for using AI OS!         ║  █
    █     │ \o/ │    ║  Keep building amazing things!   ║  █
    █     └─────┘    ║                                  ║  █
    █                ╚══════════════════════════════════╝  █
    █                                                      █
    █   ██████╗ ██╗   ██╗███████╗██╗██╗                    █
    █   ██╔══██╗╚██╗ ██╔╝██╔════╝██║██║                    █
    █   ██████╔╝ ╚████╔╝ █████╗  ██║██║                    █
    █   ██╔══██╗  ╚██╔╝  ██╔══╝  ╚═╝╚═╝                    █
    █   ██████╔╝   ██║   ███████╗██╗██╗                    █
    █   ╚═════╝    ╚═╝   ╚══════╝╚═╝╚═╝                    █
    █                                                      █
    ████████████████████████████████████████████████████████
        """
        
        while True:
            try:
                user_input = self.get_user_input().strip()
                
                if not user_input:
                    continue
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.command_history.append((timestamp, user_input))
                self.command_count += 1
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    if RICH_AVAILABLE:
                        if Confirm.ask("\n[yellow]Are you sure you want to exit?[/yellow]"):
                            console.print("\n[cyan]👋 Goodbye! Thanks for using AI OS.[/cyan]")
                            console.print(Panel(exit_banner), style="purple")
                            break
                    else:
                        confirm = input(Colors.WARNING + "\nAre you sure you want to exit? (y/n): " + Colors.ENDC)
                        if confirm.lower() == 'y':
                            print(Colors.CYAN + "\n👋 Goodbye! Thanks for using AI OS." + Colors.ENDC)
                            break
                    continue
                
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue

                elif user_input.lower() == 'config':
                    self.show_config_menu()
                    # After config, we should reload the agent, but for now we just show the menu.
                    # A full implementation would require restarting or re-initializing the agent.
                    console.print("[yellow]Please restart the application for configuration changes to take full effect.[/yellow]")
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
                    if RICH_AVAILABLE and Confirm.ask("[yellow]Start a new session? This will clear history.[/yellow]"):
                        self.command_history.clear()
                        self.command_count = 0
                        self.session_start = datetime.now()
                        self.clear_screen()
                        self.show_banner()
                    continue
                
                processed_input = self.process_special_command(user_input)
                if processed_input:
                    user_input = processed_input
                
                with console.status("[bold cyan]Processing your request...[/bold cyan]", spinner="dots"):
                    time.sleep(0.1)
                
                print()
                self.agent.print_response(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n\nUse 'exit' command to quit properly.")
                continue
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                if RICH_AVAILABLE:
                    console.print(f"\n[red]✗[/red] {error_msg}")
                else:
                    print(Colors.FAIL + f"\n✗ {error_msg}" + Colors.ENDC)
                logger.error(f"Error in main loop: {e}", exc_info=True)

def main():
    """Main entry point"""
    try:
        config = None
        if load_config:
            # create_default_config()
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
        
        # ======== DYNAMIC MODEL INITIALIZATION ========
        model_instance = None
        agent_config = config.agent

        if agent_config.provider == "openai":
            api_key = agent_config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: OpenAI API key not found in config or OPENAI_API_KEY environment variable." + Colors.ENDC)
                print("Please run 'python main.py', enter 'config', and set your key.")
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
                print("Please run 'python main.py', enter 'config', and set your key.")
                sys.exit(1)
            model_instance = Gemini(
                id=agent_config.model,
                api_key=api_key,
                temperature=agent_config.temperature,
                # max_tokens=agent_config.max_tokens
            )
        else:
            print(f"{Colors.FAIL}Error: Unknown AI provider '{agent_config.provider}' in configuration.{Colors.ENDC}")
            sys.exit(1)
        
        # ===============================================

        reasoning_agent = Agent(
            model=model_instance,
            tools=[ReasoningTools(add_instructions=True), ShellTools(), FileTools(), PythonTools()],
            instructions=dedent("""\
                system_information = {system_information}
                You are an expert System Intelligence Teminal Assistant with strong analytical, system administration, and IoT skills! 🧠
                
                You are running on the user's system and have full access to analyze and manage it through shell commands. 
                You will also be given IoT devices connected to the system to manage.
                Your role is to:
                1. Understand user queries and plan and execute commands appropriate for the current system and environment.
                2. Analyze command outputs intelligently
                3. Provide clear, actionable insights
                4. Help with system administration, monitoring, and automation
                
                Always:
                - Understand what is the current system you are working on.
                - Be concise but thorough
                - Explain technical concepts clearly
                - Suggest follow-up actions when relevant
                - Warn about potentially dangerous operations. Only move ahead if the user explicitly confirms for it.

                Note:
                - If the user asks for something which requires external connections(for eg, fetching emails from a service), come up with a plan (that can be executed from the terminal) and ask for confirmation.
                - Once the user confirms, execute the plan. Ask for more details required from the user's end if needed.
                - When user asks for something which requires saving data to files, name the file in a way that it is searchable and easy to understand. keep them into folder with date.
                - If the execution output of a command is very large, save the output to a file or write a script to process the output.
                
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