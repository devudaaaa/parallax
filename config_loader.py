"""
Central configuration loader for the Digital Twin infrastructure.
Loads from config.yaml and .env, making settings available everywhere.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml
from loguru import logger


# ── Project Root ─────────────────────────────────
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = ROOT_DIR / "config.yaml"


class Settings(BaseSettings):
    """Environment-based settings (from .env file)."""
    
    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    primary_llm_provider: str = "anthropic"
    primary_model: str = "claude-sonnet-4-20250514"
    embedding_model: str = "all-MiniLM-L6-v2"
    vision_model: str = "claude-sonnet-4-20250514"
    use_local_llm: bool = False
    local_model_name: str = "llama3.1:8b"
    
    # Vector Store
    chroma_persist_dir: str = "./data/chromadb"
    chroma_collection_name: str = "digital_twin_memory"
    
    # Data
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    
    # Twin
    twin_name: str = "Ade"
    default_access_tier: str = "public"
    
    # Platform
    api_host: str = "127.0.0.1"  # Localhost only by default — use 0.0.0.0 only behind a reverse proxy
    api_port: int = 8000
    enable_websocket: bool = True
    parallax_api_key: str = ""  # Set to enable API authentication
    cors_origins: str = ""  # Comma-separated allowed origins
    
    # Connectors
    slack_bot_token: str = ""
    slack_app_token: str = ""
    discord_bot_token: str = ""
    
    # Divergence (Phase 3)
    track_decisions: bool = True
    decision_log_dir: str = "./data/decisions"
    faith_threshold: float = 0.45
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_yaml_config() -> dict:
    """Load the main YAML configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    logger.warning(f"Config file not found at {CONFIG_FILE}, using defaults")
    return {}


def ensure_directories():
    """Create all required data directories."""
    dirs = [
        DATA_DIR / "raw" / "slack",
        DATA_DIR / "raw" / "whatsapp",
        DATA_DIR / "raw" / "discord",
        DATA_DIR / "raw" / "keybase",
        DATA_DIR / "raw" / "documents" / "pdfs",
        DATA_DIR / "raw" / "documents" / "docs",
        DATA_DIR / "raw" / "documents" / "notes",
        DATA_DIR / "raw" / "documents" / "code",
        DATA_DIR / "raw" / "photos",
        DATA_DIR / "processed",
        DATA_DIR / "chromadb",
        DATA_DIR / "decisions",
        DATA_DIR / "exports",
        DATA_DIR / "fine_tuning",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured {len(dirs)} data directories exist")


# ── Singletons ───────────────────────────────────
settings = Settings()
yaml_config = load_yaml_config()
