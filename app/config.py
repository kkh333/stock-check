from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    gmail_user: str
    gmail_app_password: str
    default_alert_to: str
    check_interval_minutes: int
    database_path: Path
    host: str
    port: int

    @property
    def check_interval_seconds(self) -> int:
        return self.check_interval_minutes * 60


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"환경 변수 {name} 이(가) 필요합니다. .env.example 을 참고하세요.")
    return value


def load_settings(*, strict_smtp: bool = False) -> Settings:
    db = os.getenv("DATABASE_PATH", "data/monitors.db")
    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pw = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if strict_smtp and (not gmail_user or not gmail_pw):
        raise RuntimeError("GMAIL_USER 와 GMAIL_APP_PASSWORD 가 필요합니다.")

    default_to = os.getenv("DEFAULT_ALERT_TO", gmail_user).strip() or gmail_user

    return Settings(
        gmail_user=gmail_user,
        gmail_app_password=gmail_pw.replace(" ", ""),
        default_alert_to=default_to,
        check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "10")),
        database_path=PROJECT_ROOT / db,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )