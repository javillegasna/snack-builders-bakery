import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.menu.repository import MenuRepository
from app.menu.schemas import MenuItemCreate, MenuItemRead, MenuItemUpdate
from app.menu.service import MenuItemInUseError, MenuItemNotFoundError, MenuService

router = APIRouter(prefix="/menu", tags=["menu"])


def get_menu_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MenuService:
    return MenuService(MenuRepository(session))


MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]


@router.get("")
async def list_menu(service: MenuServiceDep) -> list[MenuItemRead]:
    return [MenuItemRead.model_validate(item) for item in await service.list_menu()]


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Malformed request body"}},
)
async def create_item(data: MenuItemCreate, service: MenuServiceDep) -> MenuItemRead:
    return MenuItemRead.model_validate(await service.create_item(data))


@router.patch(
    "/items/{item_id}",
    responses={
        400: {"description": "Malformed request body"},
        404: {"description": "Menu item not found"},
    },
)
async def update_item(
    item_id: uuid.UUID, data: MenuItemUpdate, service: MenuServiceDep
) -> MenuItemRead:
    try:
        return MenuItemRead.model_validate(await service.update_item(item_id, data))
    except MenuItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="menu item not found"
        ) from None


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Menu item not found"},
        409: {"description": "Menu item is referenced by existing orders"},
    },
)
async def delete_item(item_id: uuid.UUID, service: MenuServiceDep) -> None:
    try:
        await service.delete_item(item_id)
    except MenuItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="menu item not found"
        ) from None
    except MenuItemInUseError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="menu item is referenced by existing orders",
        ) from None
