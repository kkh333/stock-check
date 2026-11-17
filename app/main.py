from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.adapters.registry import adapter_for_url, supported_sites
from app.config import load_settings
from app.db import Database
from app.worker import check_one_monitor, worker_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    settings = load_settings()
    app.state.settings = settings
    app.state.db = Database(settings.database_path)
    _worker_task = asyncio.create_task(worker_loop(app.state.db, settings))
    logger.info("http://%s:%s", settings.host, settings.port)
    yield
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Restock Monitor", lifespan=lifespan)


def _resolve_email(form_email: str, settings) -> str:
    email = form_email.strip()
    if email:
        return email
    if settings.default_alert_to:
        return settings.default_alert_to
    raise ValueError("알림 이메일을 입력하거나 .env 의 DEFAULT_ALERT_TO 를 설정하세요.")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db: Database = request.app.state.db
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "monitors": db.list_monitors(),
            "supported_sites": supported_sites(),
            "interval_minutes": request.app.state.settings.check_interval_minutes,
        },
    )


@app.post("/monitors")
async def create_monitor(
    request: Request,
    url: str = Form(...),
    option_label: str = Form(...),
    email: str = Form(""),
):
    settings = request.app.state.settings
    db: Database = request.app.state.db
    url = url.strip()
    try:
        adapter = adapter_for_url(url)
        meta = adapter.build_meta(url, option_label.strip())
        alert_email = _resolve_email(email, settings)
        created = db.add_monitor(
            url=url,
            option_label=meta["option_label"],
            email=alert_email,
            site=adapter.site_id,
            meta=meta,
        )
        await asyncio.to_thread(check_one_monitor, db, created.id, settings)
    except Exception as e:
        logger.warning("add monitor failed: %s", e)
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "monitors": db.list_monitors(),
                "supported_sites": supported_sites(),
                "interval_minutes": settings.check_interval_minutes,
                "error": str(e),
                "form_url": url,
                "form_option": option_label,
                "form_email": email,
            },
            status_code=400,
        )
    return RedirectResponse("/", status_code=303)


@app.post("/monitors/{monitor_id}/delete")
async def delete_monitor(request: Request, monitor_id: int):
    db: Database = request.app.state.db
    db.delete_monitor(monitor_id)
    return RedirectResponse("/", status_code=303)


@app.post("/monitors/{monitor_id}/toggle")
async def toggle_monitor(request: Request, monitor_id: int):
    db: Database = request.app.state.db
    monitor = db.get_monitor(monitor_id)
    if monitor:
        db.set_enabled(monitor_id, not monitor.enabled)
    return RedirectResponse("/", status_code=303)


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()