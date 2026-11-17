from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from app.config import Settings
from app.db import Monitor


def send_restock_alert(settings: Settings, monitor: Monitor, summary: str) -> None:
    if not settings.gmail_user or not settings.gmail_app_password:
        raise RuntimeError("Gmail SMTP 설정이 없습니다 (.env).")

    body = (
        "재입고 알림\n\n"
        f"사이트: {monitor.site}\n"
        f"옵션: {monitor.option_label}\n"
        f"상태: {summary}\n\n"
        f"{monitor.url}\n"
    )
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"[재입고] {monitor.option_label} — {monitor.site}"
    msg["From"] = settings.gmail_user
    msg["To"] = monitor.email

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.gmail_user, settings.gmail_app_password)
        smtp.send_message(msg)