import uuid

from app.menu.models import MenuItem
from app.menu.repository import MenuRepository
from app.menu.schemas import MenuItemCreate, MenuItemUpdate


class MenuItemNotFoundError(Exception):
    """Raised when a menu item id does not exist."""


class MenuService:
    def __init__(self, repository: MenuRepository) -> None:
        self._repository = repository

    async def list_menu(self) -> list[MenuItem]:
        return await self._repository.list(only_available=True)

    async def list_all(self) -> list[MenuItem]:
        return await self._repository.list()

    async def create_item(self, data: MenuItemCreate) -> MenuItem:
        return await self._repository.add(MenuItem(**data.model_dump()))

    async def update_item(self, item_id: uuid.UUID, data: MenuItemUpdate) -> MenuItem:
        item = await self._require(item_id)
        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in updates.items():
            setattr(item, field, value)
        return await self._repository.add(item)

    async def delete_item(self, item_id: uuid.UUID) -> None:
        await self._repository.delete(await self._require(item_id))

    async def _require(self, item_id: uuid.UUID) -> MenuItem:
        item = await self._repository.get(item_id)
        if item is None:
            raise MenuItemNotFoundError(str(item_id))
        return item
