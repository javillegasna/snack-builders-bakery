from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.db import SessionFactory, engine
from app.core.logging import configure_logging
from app.core.telemetry import configure_telemetry
from app.kitchen.engine import KitchenEngine
from app.kitchen.router import router as kitchen_router
from app.menu.router import router as menu_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router

_settings = get_settings()
configure_logging(_settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    kitchen_engine = KitchenEngine(SystemClock(), session_factory=SessionFactory)
    app.state.kitchen_engine = kitchen_engine
    await kitchen_engine.start()
    try:
        yield
    finally:
        await kitchen_engine.stop()


app = FastAPI(title=_settings.app_name, lifespan=lifespan)
configure_telemetry(app, _settings)

app.include_router(menu_router)
app.include_router(kitchen_router)
app.include_router(orders_router)
app.include_router(payments_router)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["ops"])
async def ready() -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}
