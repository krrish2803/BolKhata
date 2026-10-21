import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = "dev"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173"
    MONGODB_URI: str = "mongodb://localhost:27017/bolkhata_dev"
    DATABASE_NAME: str = "bolkhata"
    
    # LLM Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_RPM: int = 4
    GEMINI_DAILY_CALL_CAP: int = 500
    GEMINI_TIMEOUT_SECONDS: float = 15.0

    # NVIDIA NIM LLM
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "meta/llama-3.2-11b-vision-instruct"

    # Pluggable Model Layer
    # Models can be configured via PRIMARY_MODEL (e.g. "gemini-2.5-flash", "meta/llama-3.2-11b-vision-instruct")
    # and optional SECONDARY_MODEL.
    # The small 11B vision model must not be used as an automatic fallback (ALLOW_VISION_FALLBACK defaults to False).
    PRIMARY_PROVIDER: str = "gemini"  # "gemini" | "nvidia"
    PRIMARY_MODEL: str = "gemini-2.5-flash"
    SECONDARY_PROVIDER: str = ""      # "nvidia" | "gemini" | ""
    SECONDARY_MODEL: str = ""         # e.g. "meta/llama-3.1-70b-instruct" or ""
    ALLOW_VISION_FALLBACK: bool = False

    # Feature 4: Fuzzy Customer Matching Thresholds
    FUZZY_MATCH_AUTO_THRESHOLD: float = 92.0
    FUZZY_MATCH_ASK_THRESHOLD: float = 75.0
    ALIAS_MAX_COUNT: int = 10
    ALIAS_MAX_LENGTH: int = 40

    # Feature 5: Overdue Payment Reminder Drafts
    REMINDER_USE_LLM: bool = False

    # Security & Proxies
    TRUSTED_PROXIES: str = "127.0.0.1"  # comma-separated trusted reverse proxy IPs
    WORKSPACE_MUTATION_RPM: int = 60    # rate limit for mutating requests per workspace
    WORKSPACE_CREATION_DAILY_CAP: int = 50  # rate limit for creating workspaces per IP per day

    @property
    def trusted_proxy_list(self) -> List[str]:
        return [ip.strip() for ip in self.TRUSTED_PROXIES.split(",") if ip.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
