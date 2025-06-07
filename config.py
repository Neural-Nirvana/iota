# config.py
import os
import sqlite3
from dataclasses import dataclass, asdict, field, fields, is_dataclass
from typing import Any

# --- NEW: Using SQLite for configuration ---
# All settings will be stored in the same database as the agent sessions.
DB_FILE = "tmp/data.db" 

# --- Dataclasses remain the same ---
@dataclass
class NetworkConfig:
    wifi_ssid: str = ""
    wifi_password: str = ""
    use_proxy: bool = False
    proxy_url: str = ""
    proxy_port: int = 8080

@dataclass
class AgentConfig:
    provider: str = "openai"  # 'openai' or 'google'
    openai_api_key: str = ""
    google_api_key: str = ""
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

# --- NEW: Helper function to manage DB connection and table creation ---
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

# --- REWRITTEN: `save_config` now writes to the database ---
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

# --- REWRITTEN: `load_config` now reads from the database ---
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
            print("No configuration found in database. Creating default settings.")
            default_config = Config()
            # Also populate keys from environment variables on first run
            default_config.agent.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
            default_config.agent.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
            save_config(default_config)
            return default_config

        # Unflatten the dictionary from the database rows
        flat_config = {key: value for key, value in rows}
        nested_config_dict = _unflatten_dict(flat_config)
        
        # Recreate the Config object from the dictionary, applying correct types
        return _dict_to_config(nested_config_dict)

    except Exception as e:
        print(f"Error loading config from database: {e}. Returning default config.")
        return Config()

# --- NEW HELPER FUNCTIONS ---
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

# No longer need create_default_config as a separate public function.
# load_config handles the creation of defaults on the first run.
create_default_config = lambda: None # No-op function for compatibility