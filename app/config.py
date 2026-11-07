import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# Explicitly load .env file from project base directory
load_dotenv(BASE_DIR / ".env", override=True)

class Settings(BaseSettings):
    APP_NAME: str = "Smart Kirana Enterprise"
    APP_NAME_MR: str = "स्मार्ट किराणा"
    VERSION: str = "1.1.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Ingestion Latency SLAs
    INGESTION_TIMEOUT_MS: int = int(os.getenv("INGESTION_TIMEOUT_MS", "2000"))
    CLIENT_TIMEOUT_MS: int = int(os.getenv("CLIENT_TIMEOUT_MS", "2500"))
    
    # Circuit Breaker Config
    CIRCUIT_BREAKER_MAX_FAILURES: int = int(os.getenv("CIRCUIT_BREAKER_MAX_FAILURES", "5"))
    CIRCUIT_BREAKER_RESET_SECONDS: int = int(os.getenv("CIRCUIT_BREAKER_RESET_SECONDS", "60"))
    
    # Gemini AI Config
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def get_gemini_api_key(self) -> str:
        key = self.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        return key.strip() if key else ""

    # Database URL: Supports PostgreSQL (Supabase / psycopg2 / psycopg) or SQLite
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    def get_database_url(self) -> str:
        raw_url = (self.DATABASE_URL or os.getenv("DATABASE_URL", "")).strip()
        if raw_url:
            # Upgrade port 6543 (transaction pooler) to 5432 (session pooler)
            if ":6543" in raw_url:
                raw_url = raw_url.replace(":6543", ":5432")

            # Normalize legacy 'postgres://' schema to 'postgresql://' for SQLAlchemy 2.0+
            if raw_url.startswith("postgres://"):
                raw_url = "postgresql://" + raw_url[len("postgres://"):]

            # Enforce SSL mode for PostgreSQL
            if raw_url.startswith("postgresql"):
                if "sslmode=" not in raw_url:
                    sep = "&" if "?" in raw_url else "?"
                    raw_url = f"{raw_url}{sep}sslmode=require"
            return raw_url

        return f"sqlite:///{BASE_DIR.as_posix()}/kirana.db"

    def get_database_config(self) -> dict:
        """Parses dynamic database configuration using dj_database_url."""
        url = self.get_database_url()
        try:
            import dj_database_url
            return dj_database_url.parse(url, conn_max_age=600, ssl_require=True)
        except Exception:
            return {"ENGINE": "django.db.backends.postgresql" if url.startswith("postgres") else "django.db.backends.sqlite3", "NAME": url}
    
    # Default Buyer for local/family single ledger mode
    DEFAULT_BUYER_ID: int = int(os.getenv("DEFAULT_BUYER_ID", "1"))
    
    # Confidence thresholds (PRD 2.1.8)
    CONFIDENCE_HIGH: float = 0.85
    CONFIDENCE_MID: float = 0.60
    
    # Volatility thresholds (PRD 2.3)
    VOLATILITY_BALANCED_ABS: float = 5.0
    VOLATILITY_SURGE_GT: float = 6.0
    VOLATILITY_DIP_LT: float = -2.0
    VOLATILITY_MEDIAN_WINDOW: int = 5

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

