"""Pytest hooks: load env before any test module imports settings."""
from pathlib import Path

from dotenv import load_dotenv

_backend = Path(__file__).resolve().parent
load_dotenv(_backend / ".env", override=False)
load_dotenv(_backend.parent / ".env", override=False)
