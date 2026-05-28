import uuid

from pydantic import BaseModel


class TrayStatus(BaseModel):
    tray_id: int
    order_id: uuid.UUID | None = None
    remaining_seconds: int | None = None


class OvenStatus(BaseModel):
    oven_id: int
    trays: list[TrayStatus]


class QueueEntryStatus(BaseModel):
    position: int
    order_id: uuid.UUID
    priority_level: int


class KitchenStatus(BaseModel):
    ovens: list[OvenStatus]
    queue: list[QueueEntryStatus]
