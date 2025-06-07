import os
import json
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List

CONFIG_FILE = os.path.expanduser("~/.config/sita/config.json")

@dataclass
class NetworkConfig:
    wifi_ssid: str = ""
    wifi_password: str = ""
    use_proxy: bool = False
    proxy_url: str = ""
    proxy_port: int = 8080

@dataclass
class AgentConfig:
    api_key: str = ""
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
    db_file: str = "tmp/data.db"

@dataclass
class Config:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

def create_default_config():
    """Create default configuration file if it doesn't exist"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    if not os.path.exists(CONFIG_FILE):
        config = Config()
        
        # Check if OpenAI API key exists in environment
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            config.agent.api_key = api_key
        
        save_config(config)
        return config
    return load_config()

def load_config() -> Config:
    """Load configuration from file"""
    if not os.path.exists(CONFIG_FILE):
        return create_default_config()
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_dict = json.load(f)
        
        config = Config(
            network=NetworkConfig(**config_dict.get('network', {})),
            agent=AgentConfig(**config_dict.get('agent', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            ui=UIConfig(**config_dict.get('ui', {})),
            storage=StorageConfig(**config_dict.get('storage', {}))
        )
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return Config()

def save_config(config: Config) -> bool:
    """Save configuration to file"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(asdict(config), f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
