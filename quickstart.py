#!/usr/bin/env python3
"""
🧠 Parallax Quick Start — devudaaaa Research Lab

This script sets up the entire infrastructure and guides you through
getting your digital twin running.

Usage:
    python quickstart.py
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Colors for terminal output
class C:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🧠  D I G I T A L   T W I N                           ║
    ║       devudaaaa Research Lab                             ║
    ║                                                          ║
    ║   "Faith can be one of the core attributes that makes    ║
    ║    us a 'True Individual' in this AI era."               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
{C.END}""")


def check_python():
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"{C.RED}✗ Python 3.10+ required. You have {v.major}.{v.minor}{C.END}")
        return False
    print(f"{C.GREEN}✓ Python {v.major}.{v.minor}.{v.micro}{C.END}")
    return True


def setup_directories():
    """Create all data directories."""
    from config_loader import ensure_directories, DATA_DIR
    ensure_directories()
    print(f"{C.GREEN}✓ Data directories created at {DATA_DIR}{C.END}")
    return True


def setup_env():
    """Create .env file if it doesn't exist."""
    root = Path(__file__).parent
    env_file = root / ".env"
    example = root / ".env.example"
    
    if env_file.exists():
        print(f"{C.GREEN}✓ .env file exists{C.END}")
        return True
    
    if example.exists():
        shutil.copy(example, env_file)
        print(f"{C.YELLOW}⚠ Created .env from template. Please edit it with your API keys.{C.END}")
    else:
        print(f"{C.RED}✗ .env.example not found{C.END}")
        return False
    
    return True


def check_dependencies():
    """Check if key dependencies are installed."""
    required = {
        "chromadb": "chromadb",
        "fastapi": "fastapi",
        "anthropic": "anthropic",
        "sentence_transformers": "sentence-transformers",
        "yaml": "pyyaml",
        "loguru": "loguru",
        "pydantic": "pydantic",
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  {C.GREEN}✓ {package}{C.END}")
        except ImportError:
            print(f"  {C.RED}✗ {package}{C.END}")
            missing.append(package)
    
    if missing:
        print(f"\n{C.YELLOW}Install missing packages:{C.END}")
        print(f"  pip install {' '.join(missing)} --break-system-packages")
        return False
    
    return True


def check_api_keys():
    """Check if API keys are configured."""
    from dotenv import load_dotenv
    load_dotenv()
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    if anthropic_key and not anthropic_key.startswith("sk-ant-your"):
        print(f"{C.GREEN}✓ Anthropic API key configured{C.END}")
        return True
    elif openai_key and not openai_key.startswith("sk-your"):
        print(f"{C.GREEN}✓ OpenAI API key configured{C.END}")
        return True
    else:
        print(f"{C.YELLOW}⚠ No API keys configured. Edit .env to add your key.{C.END}")
        print(f"  {C.DIM}You can use Ollama for local inference without API keys.{C.END}")
        return False


def check_data():
    """Check if any data has been added."""
    from config_loader import DATA_DIR
    
    data_found = False
    sources = {
        "Slack": DATA_DIR / "raw" / "slack",
        "WhatsApp": DATA_DIR / "raw" / "whatsapp",
        "Discord": DATA_DIR / "raw" / "discord",
        "Keybase": DATA_DIR / "raw" / "keybase",
        "PDFs": DATA_DIR / "raw" / "documents" / "pdfs",
        "Documents": DATA_DIR / "raw" / "documents" / "docs",
        "Notes": DATA_DIR / "raw" / "documents" / "notes",
        "Code": DATA_DIR / "raw" / "documents" / "code",
        "Photos": DATA_DIR / "raw" / "photos",
    }
    
    for name, path in sources.items():
        files = list(path.glob("**/*")) if path.exists() else []
        files = [f for f in files if f.is_file()]
        if files:
            print(f"  {C.GREEN}✓ {name}: {len(files)} files{C.END}")
            data_found = True
        else:
            print(f"  {C.DIM}○ {name}: empty{C.END}")
    
    if not data_found:
        print(f"\n{C.YELLOW}No data found yet. Add your exports to get started:{C.END}")
        print(f"""
  {C.BOLD}How to export your data:{C.END}
  
  • {C.CYAN}Slack:{C.END}     Workspace Settings → Import/Export Data → Export
                  Extract to: ./data/raw/slack/
  
  • {C.CYAN}WhatsApp:{C.END}  Open chat → ⋮ → More → Export chat → Without media
                  Save to: ./data/raw/whatsapp/
  
  • {C.CYAN}Discord:{C.END}   Use DiscordChatExporter (github.com/Tyrrrz/DiscordChatExporter)
                  Export as JSON to: ./data/raw/discord/
  
  • {C.CYAN}Documents:{C.END} Drop PDFs, docs, notes into their respective folders
  
  • {C.CYAN}Photos:{C.END}    Add photos to ./data/raw/photos/ (will use vision AI)
""")
    
    return data_found


def run_status():
    """Show system status."""
    banner()
    
    print(f"\n{C.BOLD}System Check{C.END}")
    print("─" * 40)
    
    ok = True
    
    ok &= check_python()
    ok &= setup_env()
    ok &= setup_directories()
    
    print(f"\n{C.BOLD}Dependencies{C.END}")
    print("─" * 40)
    deps_ok = check_dependencies()
    
    print(f"\n{C.BOLD}Configuration{C.END}")
    print("─" * 40)
    check_api_keys()
    
    print(f"\n{C.BOLD}Data Sources{C.END}")
    print("─" * 40)
    has_data = check_data()
    
    # Next steps
    print(f"\n{'═' * 50}")
    print(f"{C.BOLD}Next Steps{C.END}")
    print(f"{'═' * 50}")
    
    if not deps_ok:
        print(f"\n  {C.CYAN}1.{C.END} Install dependencies:")
        print(f"     pip install -r requirements.txt --break-system-packages")
    
    if not has_data:
        print(f"\n  {C.CYAN}{'1' if deps_ok else '2'}.{C.END} Add your data exports to ./data/raw/")
    
    step = 2 if deps_ok else 3
    
    print(f"""
  {C.CYAN}{step}.{C.END} Run the data pipeline:
     python -m phase1_data_pipeline.run_pipeline

  {C.CYAN}{step+1}.{C.END} Start the twin (interactive mode):
     python -m phase2_logic_twin.twin

  {C.CYAN}{step+2}.{C.END} Launch the platform:
     python -m phase4_platform.api.server
     Then visit: http://localhost:8000/docs

  {C.CYAN}{step+3}.{C.END} Connect messaging (optional):
     Configure Slack/Discord tokens in .env
     python scripts/start_slack.py
""")
    
    print(f"""
{C.DIM}─── devudaaaa Research Lab ───────────────────────────
Applying game theory solutions to study human decision-making
using divine guidance as a measurable variable.
https://devudaaaa.xyz{C.END}
""")


if __name__ == "__main__":
    run_status()
