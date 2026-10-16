"""Environment configuration.

Select an environment with ENV (default: local). Values are read from
config/.env.<ENV>; any variable already set in the shell wins, so CI can
override single values without editing files, e.g.

    ENV=ci BASE_URL=http://staging.example:8080 pytest
"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    env: str
    base_url: str
    api_base_url: str
    headless: bool
    slow_mo_ms: int
    default_timeout_ms: int
    start_app: bool
    self_heal: bool
    reports_dir: Path

    @property
    def app_host(self) -> str:
        return urlparse(self.base_url).hostname or "127.0.0.1"

    @property
    def app_port(self) -> int:
        url = urlparse(self.base_url)
        return url.port or (443 if url.scheme == "https" else 80)


def load_settings() -> Settings:
    env = os.getenv("ENV", "local")
    env_file = CONFIG_DIR / f".env.{env}"
    if not env_file.exists():
        raise FileNotFoundError(f"No config for ENV={env!r}: expected {env_file}")
    load_dotenv(env_file, override=False)
    # Optional, never committed: local secrets such as an LLM API key.
    load_dotenv(CONFIG_DIR / ".env.secrets", override=False)

    def required(name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"{name} is not set in {env_file.name} or the environment")
        return value.rstrip("/")

    return Settings(
        env=env,
        base_url=required("BASE_URL"),
        api_base_url=required("API_BASE_URL"),
        headless=_bool("HEADLESS", "true"),
        slow_mo_ms=int(os.getenv("SLOW_MO_MS", "0")),
        default_timeout_ms=int(os.getenv("DEFAULT_TIMEOUT_MS", "10000")),
        start_app=_bool("START_APP", "true"),
        self_heal=_bool("SELF_HEAL", "false"),
        reports_dir=PROJECT_ROOT / os.getenv("REPORTS_DIR", "reports"),
    )
