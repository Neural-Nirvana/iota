# config.py - Enhanced with OpenRouter & Together AI Support
import os
import sqlite3
from dataclasses import dataclass, asdict, field, fields, is_dataclass
from typing import Any

# --- NEW: Using SQLite for configuration ---
# All settings will be stored in the same database as the agent sessions.
DB_FILE = "tmp/data.db" 

# --- Enhanced Dataclasses with new providers ---
@dataclass
class NetworkConfig:
    wifi_ssid: str = ""
    wifi_password: str = ""
    use_proxy: bool = False
    proxy_url: str = ""
    proxy_port: int = 8080

@dataclass
class AgentConfig:
    provider: str = "openai"  # 'openai', 'google', 'openrouter', 'together'
    openai_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""      # NEW: OpenRouter API key
    together_api_key: str = ""        # NEW: Together AI API key
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000

@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/sita.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class UIConfig:
    show_tool_calls: bool = True
    markdown: bool = True
    theme: str = "default"

@dataclass
class StorageConfig:
    # This now defines the DB file for both config and agent history.
    db_file: str = DB_FILE

@dataclass
class Config:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

# --- Helper function to manage DB connection and table creation ---
def _get_db_conn():
    """Gets a DB connection and ensures the settings table exists."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    return conn

# --- Enhanced `save_config` with new API keys ---
def save_config(config: Config) -> bool:
    """Save configuration to the SQLite database."""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        
        config_dict = asdict(config)
        
        # Flatten the dictionary for key-value storage
        # e.g., {'agent': {'model': 'gpt-4'}} becomes {'agent.model': 'gpt-4'}
        flat_config = _flatten_dict(config_dict)

        # Use INSERT OR REPLACE to update existing keys or insert new ones
        for key, value in flat_config.items():
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)) # Store all values as strings
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving config to database: {e}")
        return False

# --- Enhanced `load_config` with migration support ---
def load_config() -> Config:
    """Load configuration from the SQLite database. Creates default if not present."""
    try:
        conn = _get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            # No settings found, create and save the default config
            print("No configuration found in database. Creating default settings with multi-provider support.")
            default_config = Config()
            # Populate keys from environment variables on first run
            default_config.agent.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
            default_config.agent.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
            default_config.agent.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
            default_config.agent.together_api_key = os.environ.get("TOGETHER_API_KEY", "")
            save_config(default_config)
            return default_config

        # Unflatten the dictionary from the database rows
        flat_config = {key: value for key, value in rows}
        nested_config_dict = _unflatten_dict(flat_config)
        
        # Recreate the Config object from the dictionary, applying correct types
        config = _dict_to_config(nested_config_dict)
        
        # Migration: Add new API key fields if they don't exist
        if not hasattr(config.agent, 'openrouter_api_key'):
            config.agent.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not hasattr(config.agent, 'together_api_key'):
            config.agent.together_api_key = os.environ.get("TOGETHER_API_KEY", "")
        
        return config

    except Exception as e:
        print(f"Error loading config from database: {e}. Returning default config.")
        default_config = Config()
        # Ensure all API keys are populated from environment
        default_config.agent.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        default_config.agent.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        default_config.agent.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        default_config.agent.together_api_key = os.environ.get("TOGETHER_API_KEY", "")
        return default_config

# --- Helper Functions (unchanged) ---
def _flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flattens a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def _unflatten_dict(d: dict, sep: str = '.') -> dict:
    """Unflattens a dictionary with dot-separated keys."""
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        d_ref = result
        for part in parts[:-1]:
            if part not in d_ref:
                d_ref[part] = {}
            d_ref = d_ref[part]
        d_ref[parts[-1]] = value
    return result

def _dict_to_config(d: dict) -> Config:
    """Recursively converts a dictionary to nested dataclasses with type casting."""
    def _convert_node(node_data: dict, node_class: Any):
        if not is_dataclass(node_class):
            return node_data
        
        field_types = {f.name: f.type for f in fields(node_class)}
        converted_data = {}

        for key, value in node_data.items():
            if key not in field_types:
                continue
            
            field_type = field_types[key]
            
            # If the field is another dataclass, recurse
            if is_dataclass(field_type):
                converted_data[key] = _convert_node(value, field_type)
            else:
                # Type casting for primitive types
                try:
                    if field_type is bool:
                        converted_data[key] = str(value).lower() in ['true', '1', 'yes']
                    else:
                        converted_data[key] = field_type(value)
                except (ValueError, TypeError):
                    # Fallback to the original value if casting fails
                    converted_data[key] = value

        return node_class(**converted_data)

    return _convert_node(d, Config)

# ---------------------------------------------------------------------------
# 🔑  Enhanced API Key Management for Multiple Providers
# ---------------------------------------------------------------------------
from pathlib import Path
import os, sys
try:
    from rich.prompt import Prompt  # nice colour prompt if Rich is bundled
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    Prompt = None
    Console = None

APP_DIR   = Path.home() / ".ai-os"           # ~/.ai-os/
CFG_FILE  = APP_DIR / "settings.toml"        # Enhanced settings file

def get_openai_api_key() -> str:
    """Enhanced API key management with multi-provider support"""
    # 1 · environment variable still has top priority
    key = os.getenv("OPENAI_API_KEY")

    # 2 · fall back to the config file
    if not key and CFG_FILE.exists():
        import tomllib
        config_data = tomllib.loads(CFG_FILE.read_text())
        key = config_data.get("OPENAI_API_KEY")

    # 3 · interactive fallback with enhanced UI
    if not key:
        if Console:
            console = Console()
            console.print(Panel.fit(
                "[bold cyan]🔑 AI OS Enhanced Setup[/bold cyan]\n\n"
                "OpenAI API key not found. You can:\n"
                "• Get one at [blue]https://platform.openai.com/api-keys[/blue]\n"
                "• Or configure other providers (Google, OpenRouter, Together AI) later",
                border_style="bright_blue"
            ))
        else:
            print("\n🔑  OpenAI API key not found.")
            print("    You can get one at https://platform.openai.com/api-keys")
            print("    Or configure other providers later via 'config' command\n")

        if Prompt:
            key = Prompt.ask("[bold cyan]Paste your OpenAI API key (or press ↵ to continue without)[/]")
        else:
            key = input("Paste your OpenAI API key (leave blank to continue) > ").strip()

        if key:
            # Save it for next time (chmod 600 for privacy)
            APP_DIR.mkdir(exist_ok=True)
            
            # Enhanced settings file with all providers
            settings_content = f'''# AI OS Enhanced - Multi-Provider Configuration
OPENAI_API_KEY = "{key}"

# Uncomment and set these when you get API keys for other providers:
# GOOGLE_API_KEY = "your-google-key-here"
# OPENROUTER_API_KEY = "your-openrouter-key-here"  
# TOGETHER_API_KEY = "your-together-key-here"

# Provider URLs:
# Google: https://makersuite.google.com/app/apikey
# OpenRouter: https://openrouter.ai/keys
# Together AI: https://api.together.xyz/settings/api-keys
'''
            
            CFG_FILE.write_text(settings_content)
            CFG_FILE.chmod(0o600)
            
            if Console:
                console = Console()
                console.print("[bright_green]✅ API key saved to ~/.ai-os/settings.toml[/bright_green]")
                console.print("[dim]You can configure additional providers via the 'config' command[/dim]")
            else:
                print("✅  API key saved to ~/.ai-os/settings.toml")
                print("    You can configure additional providers via the 'config' command")
        else:
            if Console:
                console = Console()
                console.print("[yellow]⚠️  No OpenAI key provided. You can set up any provider via 'config' command.[/yellow]")
            else:
                print("⚠️  No OpenAI key provided. You can set up any provider via 'config' command.")

    # 4 · expose to environment for compatibility
    if key:
        os.environ["OPENAI_API_KEY"] = key
    
    return key or ""

def get_api_keys():
    """Load all API keys from various sources"""
    keys = {}
    
    # Try environment variables first
    keys['openai'] = os.getenv("OPENAI_API_KEY", "")
    keys['google'] = os.getenv("GOOGLE_API_KEY", "")
    keys['openrouter'] = os.getenv("OPENROUTER_API_KEY", "")
    keys['together'] = os.getenv("TOGETHER_API_KEY", "")
    
    # Try config file
    if CFG_FILE.exists():
        try:
            import tomllib
            config_data = tomllib.loads(CFG_FILE.read_text())
            for provider in ['openai', 'google', 'openrouter', 'together']:
                env_key = f"{provider.upper()}_API_KEY"
                if not keys[provider] and env_key in config_data:
                    keys[provider] = config_data[env_key]
                    # Also set in environment for consistency
                    os.environ[env_key] = config_data[env_key]
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    return keys

# Backwards compatibility
create_default_config = lambda: None