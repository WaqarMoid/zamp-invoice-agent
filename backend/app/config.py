from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ENV = Path(__file__).resolve().parent.parent / ".env"
_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
_ROOT_ENV_LOCAL = Path(__file__).resolve().parent.parent.parent / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_BACKEND_ENV, _ROOT_ENV, _ROOT_ENV_LOCAL, ".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core environment
    DATABASE_URL: str = "sqlite:///./data/app.db"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_PROVIDER: str = "gemini"
    EXTRACTION_CACHE: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    DEMO_MODE: bool = True
    LOG_LEVEL: str = "INFO"

    # Business rules thresholds (doc 07 §7.3)
    PRICE_TOLERANCE_PCT: float = 1.0  # percent
    PRICE_TOLERANCE_ABS_INR: float = 1000.00  # rupees; line tolerance = min(pct, abs)
    ROUNDING_TOLERANCE_INR: float = 1.00
    EXTRACTION_MIN_CONFIDENCE: float = 0.80
    VENDOR_NAME_MATCH_MIN: float = 88.0  # rapidfuzz token_set_ratio, 0-100
    LINE_MATCH_MIN_SCORE: float = 0.60
    PO_INFER_MIN_SCORE: float = 0.75
    PO_INFER_MIN_MARGIN: float = 0.15
    NEAR_DUP_WINDOW_DAYS: int = 30
    MAX_INVOICE_AGE_DAYS: int = 365
    AUTO_APPROVE_INFERRED_PO: bool = False
    BUYER_STATE_CODE: str = "29"
    BUYER_GSTIN: str = "29AAACK4521M1ZD"

    @property
    def allowed_origins_list(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
