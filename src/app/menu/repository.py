import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.menu.models import MenuItem


class MenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, only_available: bool = False) -> list[MenuItem]:
        stmt = select(MenuItem).order_by(MenuItem.name)
        if only_available:
            stmt = stmt.where(MenuItem.available.is_(True))
        result = await self._session.scalars(stmt)
        return list(result)

    async def get(self, item_id: uuid.UUID) -> MenuItem | None:
        return await self._session.get(MenuItem, item_id)

    async def add(self, item: MenuItem) -> MenuItem:
        self._session.add(item)
        await self._session.commit()
        return item

    async def delete(self, item: MenuItem) -> None:
        await self._session.delete(item)
        await self._session.commit()
