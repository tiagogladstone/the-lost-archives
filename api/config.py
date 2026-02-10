from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"

# Environment
def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if val is None:
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {key}")
    return val

SUPABASE_URL: str = _require_env("SUPABASE_URL")
SUPABASE_KEY: str = _require_env("SUPABASE_KEY")
GOOGLE_API_KEY: str = _require_env("GOOGLE_API_KEY")
API_KEY: str = os.environ.get("API_KEY", "dev-key-change-me")
PORT: int = int(os.environ.get("PORT", "8000"))
YOUTUBE_TOKEN_JSON: str | None = os.environ.get("YOUTUBE_TOKEN_JSON")

# YAML configs (loaded once at import time)
def _load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

SETTINGS: dict = _load_yaml("settings.yaml")
VOICES: dict = _load_yaml("voices.yaml")
PROMPTS: dict = _load_yaml("prompts.yaml")

# Derived settings
GEMINI_MODEL: str = SETTINGS.get("gemini_model", "gemini-2.0-flash")
DEFAULT_LANGUAGE: str = SETTINGS.get("default_language", "en")
VIDEO_RESOLUTION: str = SETTINGS.get("video_resolution", "1920x1080")
MUSIC_VOLUME: float = SETTINGS.get("music_volume", 0.15)
