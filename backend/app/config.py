import os
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent
UPLOAD_DIR    = BASE_DIR / "uploads"
DB_PATH       = BASE_DIR / "paperpilot.db"
DATABASE_URL  = f"sqlite:///{DB_PATH}"

# ── Load .env ──────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()

# ── LLM Provider ───────────────────────────────────────────────────────
LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "anthropic")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL   = os.getenv("OPENAI_BASE_URL", "")
LLM_MODEL         = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
LLM_MAX_TOKENS    = int(os.getenv("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE   = float(os.getenv("LLM_TEMPERATURE", "0.2"))
# Comma-separated fallback model IDs tried in order when the primary returns empty.
_fallback_raw     = os.getenv("LLM_FALLBACK_MODELS", "")
LLM_FALLBACK_MODELS: list[str] = [m.strip() for m in _fallback_raw.split(",") if m.strip()]

# ── Parsing Limits ─────────────────────────────────────────────────────
MAX_PAGES              = 40
MAX_CHARS_PER_LLM_CALL = 60000

# ── Section Headers to Detect ──────────────────────────────────────────
KNOWN_SECTION_HEADERS = [
    "abstract", "introduction", "related work", "background",
    "methodology", "method", "approach", "experiments",
    "results", "evaluation", "discussion", "conclusion",
    "limitations", "future work", "references",
]

# ── API ────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:3000"]

# ── Flashcards ─────────────────────────────────────────────────────────
FLASHCARD_COUNT_TARGET = 12
VIVA_QUESTIONS_PER_TIER = 3
