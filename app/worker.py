from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.adapters.registry import adapter_for_url
from app.config import load_settings
from app.db import Database
from app.mailer import send_restock_alert

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def check_one_monitor(db: Database, monitor_id: int, settings: Settings) -> None:
    monitor = db.get_monitor(monitor_id)
    if monitor is None or not monitor.enabled:
        return

    adapter = adapter_for_url(monitor.url)
    try:
        result = adapter.check(monitor.meta)
        was_in_stock = monitor.last_in_stock is True
        db.update_check_result(
            monitor.id,
            in_stock=result.in_stock,
            summary=result.summary,
            error=None,
        )
        if result.in_stock and not was_in_stock:
            send_restock_alert(settings, monitor, result.summary)
            logger.info("알림 발송 monitor_id=%s", monitor.id)
    except Exception as e:
        logger.exception("check failed monitor_id=%s", monitor.id)
        db.update_check_result(
            monitor.id,
            in_stock=monitor.last_in_stock or False,
            summary=monitor.last_summary or "확인 실패",
            error=str(e),
        )


def run_check_cycle(db: Database, settings: Settings) -> None:
    for monitor in db.list_monitors():
        if monitor.enabled:
            check_one_monitor(db, monitor.id, settings)


async def worker_loop(db: Database, settings: Settings) -> None:
    interval = settings.check_interval_seconds
    logger.info("워커 시작 — %s분마다 확인", settings.check_interval_minutes)

    await asyncio.to_thread(run_check_cycle, db, settings)
    while True:
        await asyncio.sleep(interval)
        await asyncio.to_thread(run_check_cycle, db, settings)


def run_worker_blocking() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    db = Database(settings.database_path)
    interval = settings.check_interval_seconds
    logger.info("워커 시작 — %s분마다 확인", settings.check_interval_minutes)
    import time

    while True:
        run_check_cycle(db, settings)
        time.sleep(interval)