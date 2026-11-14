from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(PROJECT_ENV_FILE)
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "config")) if Path(os.getenv("CONFIG_DIR", "config")).is_absolute() else PROJECT_ROOT / Path(os.getenv("CONFIG_DIR", "config"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "workspace")) if Path(os.getenv("WORKSPACE_DIR", "workspace")).is_absolute() else PROJECT_ROOT / Path(os.getenv("WORKSPACE_DIR", "workspace"))
SESSION_DIR = Path(os.getenv("SESSION_DIR", "sessions")) if Path(os.getenv("SESSION_DIR", "sessions")).is_absolute() else PROJECT_ROOT / Path(os.getenv("SESSION_DIR", "sessions"))

class ConfigError(RuntimeError):
    pass

@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    timeout: float = 60.0
    max_tool_rounds: int = 15
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> Config:
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ConfigError(
                "API_KEY 未设置。请在 .env 或环境变量中配置。"
            )

        return cls(
            api_key=api_key,
            base_url=os.getenv("BASE_URL", "https://api.deepseek.com").rstrip("/"),
            model=os.getenv("MODEL", "deepseek-flash"),
            timeout=float(os.getenv("AGENT_MAX_SHELL_TIMEOUT", "60")),
            max_tool_rounds=int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "15")),
        )
