"""
Shared configuration loader for all modules.
Loads environment variables from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key.startswith("sk-your"):
        raise ValueError(
            "Please set OPENAI_API_KEY in your .env file. "
            "Copy .env.example to .env and add your key."
        )
    return key


def get_model_name() -> str:
    """Get the OpenAI model name to use."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
