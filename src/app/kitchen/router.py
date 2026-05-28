from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.kitchen.engine import KitchenEngine
from app.kitchen.schemas import KitchenStatus

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


def get_engine(request: Request) -> KitchenEngine:
    engine: KitchenEngine = request.app.state.kitchen_engine
    return engine


KitchenEngineDep = Annotated[KitchenEngine, Depends(get_engine)]


@router.get("/status")
async def kitchen_status(engine: KitchenEngineDep) -> KitchenStatus:
    return await engine.status()
