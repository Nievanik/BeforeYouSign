"""Only module that reads the environment (see docs/file-structure.md)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")
VEXCEL_API_KEY = os.getenv("VEXCEL_API_KEY", "")
MATTERPORT_API_KEY = os.getenv("MATTERPORT_API_KEY", "")
MATTERPORT_API_TOKEN = os.getenv("MATTERPORT_API_TOKEN", "")
OFFLINE = os.getenv("OFFLINE") == "1"
