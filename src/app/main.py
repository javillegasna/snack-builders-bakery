from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.menu.router import router as menu_router

app = FastAPI(title=get_settings().app_name)

app.include_router(menu_router)


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
