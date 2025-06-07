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
from agno.tools.reasoning import ReasoningTools
from agno.tools import tool
from agno.utils.log import logger
from agno.tools.shell import ShellTools
from agno.storage.sqlite import SqliteStorage

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
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🤖 SITA-System Intelligence Terminal Assistant🤖     ║
║                                                              ║
║              Expert System Analysis & Automation             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        
        if RICH_AVAILABLE:
            console.print(Panel(banner, style="bold cyan"))
            console.print("[dim]Type 'help' for commands, 'exit' to quit[/dim]\n")
        else:
            print(Colors.CYAN + banner + Colors.ENDC)
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
            # This is a placeholder - you'd need to implement actual export logic
            # based on how the agent stores conversation history
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
        # Direct shell command execution
        if user_input.startswith('!'):
            shell_cmd = user_input[1:].strip()
            return f"Execute this shell command and show the results: {shell_cmd}"
        
        # Quick system query
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
                
                # Create configuration table
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim", width=3)
                table.add_column("Setting", style="bold")
                table.add_column("Value", style="cyan")
                
                # Network section
                table.add_row("", "[yellow bold]Network Settings[/yellow bold]", "")
                table.add_row("1", "WiFi SSID", config.network.wifi_ssid or "[italic](Not configured)[/italic]")
                table.add_row("2", "WiFi Password", "****" if config.network.wifi_password else "[italic](Not configured)[/italic]")
                table.add_row("3", "Use Proxy", str(config.network.use_proxy))
                table.add_row("4", "Proxy URL", config.network.proxy_url or "[italic](Not configured)[/italic]")
                table.add_row("5", "Proxy Port", str(config.network.proxy_port))
                
                # Agent section
                table.add_row("", "[yellow bold]Agent Settings[/yellow bold]", "")
                table.add_row("6", "OpenAI API Key", "****" + config.agent.api_key[-4:] if config.agent.api_key else "[italic](Not configured)[/italic]")
                table.add_row("7", "Model", config.agent.model)
                table.add_row("8", "Temperature", str(config.agent.temperature))
                table.add_row("9", "Max Tokens", str(config.agent.max_tokens))
                
                # UI section
                table.add_row("", "[yellow bold]UI Settings[/yellow bold]", "")
                table.add_row("10", "Show Tool Calls", str(config.ui.show_tool_calls))
                table.add_row("11", "Enable Markdown", str(config.ui.markdown))
                table.add_row("12", "Theme", config.ui.theme)
                
                console.print(table)
                console.print("\n[dim]Enter setting number to change, or 'save' to save and exit, or 'exit' to exit without saving[/dim]")
            else:
                print(Colors.HEADER + "Configuration Menu" + Colors.ENDC + "\n")
                
                # Network section
                print(Colors.CYAN + "Network Settings:" + Colors.ENDC)
                print(f"  1. WiFi SSID:      {config.network.wifi_ssid or '(Not configured)'}")
                print(f"  2. WiFi Password:   {'****' if config.network.wifi_password else '(Not configured)'}")
                print(f"  3. Use Proxy:       {config.network.use_proxy}")
                print(f"  4. Proxy URL:       {config.network.proxy_url or '(Not configured)'}")
                print(f"  5. Proxy Port:      {config.network.proxy_port}")
                
                # Agent section
                print("\n" + Colors.CYAN + "Agent Settings:" + Colors.ENDC)
                print(f"  6. OpenAI API Key: {'****' + config.agent.api_key[-4:] if config.agent.api_key else '(Not configured)'}")
                print(f"  7. Model:           {config.agent.model}")
                print(f"  8. Temperature:     {config.agent.temperature}")
                print(f"  9. Max Tokens:      {config.agent.max_tokens}")
                
                # UI section
                print("\n" + Colors.CYAN + "UI Settings:" + Colors.ENDC)
                print(f"  10. Show Tool Calls: {config.ui.show_tool_calls}")
                print(f"  11. Enable Markdown: {config.ui.markdown}")
                print(f"  12. Theme:           {config.ui.theme}")
                
                print("\nEnter setting number to change, or 'save' to save and exit, or 'exit' to exit without saving")
            
            choice = input("\nChoice: ").strip().lower()
            
            if choice == 'exit':
                return
            elif choice == 'save':
                if save_config(config):
                    if RICH_AVAILABLE:
                        console.print("[green]Configuration saved successfully![/green]")
                    else:
                        print(Colors.GREEN + "Configuration saved successfully!" + Colors.ENDC)
                    time.sleep(1.5)
                    return
                else:
                    if RICH_AVAILABLE:
                        console.print("[red]Error saving configuration[/red]")
                    else:
                        print(Colors.FAIL + "Error saving configuration" + Colors.ENDC)
                    time.sleep(1.5)
            elif choice.isdigit():
                option = int(choice)
                
                # Network settings
                if option == 1:
                    config.network.wifi_ssid = self._get_input("Enter WiFi SSID: ", config.network.wifi_ssid)
                elif option == 2:
                    config.network.wifi_password = self._get_password("Enter WiFi Password: ")
                elif option == 3:
                    config.network.use_proxy = self._get_boolean("Use proxy? (y/n): ", config.network.use_proxy)
                elif option == 4:
                    config.network.proxy_url = self._get_input("Enter Proxy URL: ", config.network.proxy_url)
                elif option == 5:
                    config.network.proxy_port = self._get_int("Enter Proxy Port: ", config.network.proxy_port)
                
                # Agent settings
                elif option == 6:
                    config.agent.api_key = self._get_password("Enter OpenAI API Key: ")
                elif option == 7:
                    models = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
                    if RICH_AVAILABLE:
                        for i, model in enumerate(models):
                            console.print(f"  {i+1}. {model}")
                        choice = Prompt.ask("Select model", default=str(models.index(config.agent.model)+1 if config.agent.model in models else 1))
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            config.agent.model = models[int(choice)-1]
                    else:
                        for i, model in enumerate(models):
                            print(f"  {i+1}. {model}")
                        choice = input(f"Select model (1-{len(models)}): ")
                        if choice.isdigit() and 1 <= int(choice) <= len(models):
                            config.agent.model = models[int(choice)-1]
                elif option == 8:
                    config.agent.temperature = self._get_float("Enter Temperature (0.0-1.0): ", config.agent.temperature)
                elif option == 9:
                    config.agent.max_tokens = self._get_int("Enter Max Tokens: ", config.agent.max_tokens)
                
                # UI settings
                elif option == 10:
                    config.ui.show_tool_calls = self._get_boolean("Show Tool Calls? (y/n): ", config.ui.show_tool_calls)
                elif option == 11:
                    config.ui.markdown = self._get_boolean("Enable Markdown? (y/n): ", config.ui.markdown)
                elif option == 12:
                    themes = ["default", "dark", "light", "system"]
                    if RICH_AVAILABLE:
                        for i, theme in enumerate(themes):
                            console.print(f"  {i+1}. {theme}")
                        choice = Prompt.ask("Select theme", default=str(themes.index(config.ui.theme)+1 if config.ui.theme in themes else 1))
                        if choice.isdigit() and 1 <= int(choice) <= len(themes):
                            config.ui.theme = themes[int(choice)-1]
                    else:
                        for i, theme in enumerate(themes):
                            print(f"  {i+1}. {theme}")
                        choice = input(f"Select theme (1-{len(themes)}): ")
                        if choice.isdigit() and 1 <= int(choice) <= len(themes):
                            config.ui.theme = themes[int(choice)-1]
    
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
            # Fallback if getpass fails
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
        
        while True:
            try:
                # Get user input
                user_input = self.get_user_input().strip()
                
                if not user_input:
                    continue
                
                # Record in history
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.command_history.append((timestamp, user_input))
                self.command_count += 1
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    if RICH_AVAILABLE:
                        if Confirm.ask("\n[yellow]Are you sure you want to exit?[/yellow]"):
                            console.print("\n[cyan]👋 Goodbye! Thanks for using System Intelligence Terminal.[/cyan]")
                            break
                    else:
                        confirm = input(Colors.WARNING + "\nAre you sure you want to exit? (y/n): " + Colors.ENDC)
                        if confirm.lower() == 'y':
                            print(Colors.CYAN + "\n👋 Goodbye! Thanks for using System Intelligence Terminal." + Colors.ENDC)
                            break
                    continue
                
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue

                elif user_input.lower() == 'config':
                    self.show_config_menu()
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
                    if RICH_AVAILABLE:
                        if Confirm.ask("[yellow]Start a new session? This will clear history.[/yellow]"):
                            self.command_history.clear()
                            self.command_count = 0
                            self.session_start = datetime.now()
                            self.clear_screen()
                            self.show_banner()
                    else:
                        confirm = input(Colors.WARNING + "Start a new session? This will clear history. (y/n): " + Colors.ENDC)
                        if confirm.lower() == 'y':
                            self.command_history.clear()
                            self.command_count = 0
                            self.session_start = datetime.now()
                            self.clear_screen()
                            self.show_banner()
                    continue
                
                # Process special prefixes
                processed_input = self.process_special_command(user_input)
                if processed_input:
                    user_input = processed_input
                
                # Show thinking indicator and run agent
                if RICH_AVAILABLE:
                    # Use a simple spinner instead of Progress to avoid Live display conflicts
                    with console.status("[bold cyan]Processing your request...[/bold cyan]", spinner="dots"):
                        # Small delay to show the spinner
                        time.sleep(0.1)
                    
                    # Now run the agent after the spinner is done
                    print()  # New line before response
                    
                    # Temporarily disable console to avoid conflicts
                    try:
                        self.agent.print_response(user_input)
                    except Exception as e:
                        # If there's still a display conflict, fall back to non-Rich output
                        console.print(f"[yellow]Note: Falling back to simple output due to display conflict[/yellow]")
                        # Try to get the response as string and print it
                        try:
                            response = self.agent.run(user_input)
                            if response and hasattr(response, 'content'):
                                print(response.content)
                            else:
                                print(str(response))
                        except Exception as inner_e:
                            raise inner_e
                else:
                    self.display_thinking()
                    print()  # New line before response
                    self.agent.print_response(user_input)
                
                print()  # Extra line for spacing
                
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
        # Load configuration
        config = None
        if load_config:
            create_default_config()
            config = load_config()
            
            # Setup logging based on configuration
            os.makedirs(os.path.dirname(config.logging.file), exist_ok=True)
            logging.basicConfig(
                level=getattr(logging, config.logging.level),
                format=config.logging.format,
                handlers=[
                    logging.FileHandler(config.logging.file),
                    logging.StreamHandler()
                ]
            )
        
        # Create necessary directories
        os.makedirs("tmp", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("exports", exist_ok=True)
        
        # Initialize agent with configuration
        if config and config.agent.api_key:
            model_config = {
                "id": config.agent.model,
                "api_key": config.agent.api_key,
                "temperature": config.agent.temperature,
                "max_tokens": config.agent.max_tokens
            }
        else:
            # Fallback to environment variable
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print(Colors.FAIL + "Error: OPENAI_API_KEY not found in environment or config!" + Colors.ENDC)
                print("Please set your OpenAI API key:")
                print("  export OPENAI_API_KEY='your-key-here'")
                print("  or create a .env file with: OPENAI_API_KEY=your-key-here")
                sys.exit(1)
            
            model_config = {"id": "gpt-4o-mini", "api_key": api_key}
        
        # Create agent with configuration
        reasoning_agent = Agent(
            model=OpenAIChat(**model_config),
            tools=[ReasoningTools(add_instructions=True), ShellTools()],
            instructions=dedent("""\
                You are an expert System Intelligence Terminal Assistant with strong analytical, system administration, and IoT skills! 🧠
                
                You are running on the user's system and have full access to analyze and manage it through shell commands.
                Your role is to:
                1. Understand system queries and execute appropriate commands
                2. Analyze command outputs intelligently
                3. Provide clear, actionable insights
                4. Help with system administration, monitoring, and automation
                
                Key capabilities:
                • System information and diagnostics
                • Process and resource management  
                • Network analysis and configuration
                • File system operations
                • Security auditing
                • Performance monitoring
                • IoT device management
                
                Always:
                - Be concise but thorough
                - Explain technical concepts clearly
                - Suggest follow-up actions when relevant
                - Warn about potentially dangerous operations
                
                Format your responses with clear sections and use markdown for readability.
            """),
            add_datetime_to_instructions=True,
            stream_intermediate_steps=config.ui.show_tool_calls if config else True,
            show_tool_calls=config.ui.show_tool_calls if config else True,
            markdown=config.ui.markdown if config else True,
            storage=SqliteStorage(
                table_name="reasoning_agent_sessions", 
                db_file=config.storage.db_file if config else "tmp/data.db"
            ),
            add_history_to_messages=True,
            num_history_runs=3,
        )
        
        # Initialize and run the enhanced UI
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