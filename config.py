"""Shared configuration and small persistence helpers."""
import os
import json
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

AUTH_FILE = DATA_DIR / "auth.json"       # saved browser session (Playwright storage_state)
CASES_FILE = DATA_DIR / "cases.json"     # crawled project cases
STATE_FILE = DATA_DIR / "state.json"     # config overrides + generated messages

PROJECTS_URL = os.getenv("PROJECTS_URL", "https://sys.rcx18.com/projects")

# --- AI provider settings ---------------------------------------------------
# Keys / hosts are read from the environment; the active provider + model are
# part of the editable config (env is just the default).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Default model per provider (used when the model field is left blank).
PROVIDER_DEFAULTS = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.1",
    "anthropic": "claude-opus-4-8",
}

DEFAULT_CONFIG = {
    "provider": os.getenv("AI_PROVIDER", "gemini").strip().lower(),
    "model": os.getenv("AI_MODEL", "").strip(),   # blank = provider default
    "email_base": os.getenv("EMAIL_BASE", "abcd"),
    "email_domain": os.getenv("EMAIL_DOMAIN", "gmail.com"),
    "start_index": int(os.getenv("START_INDEX", "1") or "1"),
}


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_cases():
    return _read_json(CASES_FILE, [])


def save_cases(cases):
    CASES_FILE.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")


def load_state():
    state = _read_json(STATE_FILE, {})
    config = dict(DEFAULT_CONFIG)
    config.update(state.get("config", {}))
    return {"config": config, "messages": state.get("messages", {})}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def build_email(config, idx):
    """Compute the rotating contact email for a case at 0-based position `idx`."""
    number = int(config["start_index"]) + int(idx)
    return f"{config['email_base']}+{number}@{config['email_domain']}"
