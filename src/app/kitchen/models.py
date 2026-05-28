import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime

OVENS = 2
TRAYS_PER_OVEN = 3
SLOT_COUNT = OVENS * TRAYS_PER_OVEN


class PriorityLevel(enum.IntEnum):
    VIP = 1
    APP = 2
    WALK_IN = 3


class TaskState(enum.StrEnum):
    QUEUED = "queued"
    BAKING = "baking"
    DONE = "done"


@dataclass
class BakeTask:
    order_id: uuid.UUID
    priority: PriorityLevel
    bake_seconds: int
    seq: int
    state: TaskState = TaskState.QUEUED
    started_at: datetime | None = None
    finish_at: datetime | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class Slot:
    oven_id: int
    tray_id: int
    task: BakeTask | None = None
    free_at: datetime | None = None

    @property
    def busy(self) -> bool:
        return self.task is not None
