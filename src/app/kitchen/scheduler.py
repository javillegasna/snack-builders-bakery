import heapq
import uuid
from datetime import datetime, timedelta

from app.kitchen.models import (
    OVENS,
    TRAYS_PER_OVEN,
    BakeTask,
    Slot,
    TaskState,
)

QueueEntry = tuple[int, int, BakeTask]


class Scheduler:
    def __init__(self) -> None:
        self._slots: list[Slot] = [
            Slot(oven_id=oven, tray_id=tray)
            for oven in range(1, OVENS + 1)
            for tray in range(1, TRAYS_PER_OVEN + 1)
        ]
        self._queue: list[QueueEntry] = []

    @property
    def slots(self) -> list[Slot]:
        return self._slots

    @property
    def queue(self) -> list[BakeTask]:
        return [task for _, _, task in sorted(self._queue)]

    def enqueue(self, task: BakeTask) -> None:
        heapq.heappush(self._queue, (int(task.priority), task.seq, task))

    def tick(self, now: datetime) -> list[BakeTask]:
        completed = self._complete_finished(now)
        self._fill_free_slots(now)
        return completed

    def estimate(self, now: datetime) -> dict[uuid.UUID, datetime]:
        free_heap: list[datetime] = []
        ready: dict[uuid.UUID, datetime] = {}
        for slot in self._slots:
            if slot.task is not None and slot.task.finish_at is not None:
                finish = slot.task.finish_at
                ready[slot.task.order_id] = max(
                    ready.get(slot.task.order_id, finish), finish
                )
                heapq.heappush(free_heap, finish)
            else:
                heapq.heappush(free_heap, now)
        for _, _, task in sorted(self._queue):
            free_at = heapq.heappop(free_heap)
            finish = max(free_at, now) + timedelta(seconds=task.bake_seconds)
            previous = ready.get(task.order_id)
            ready[task.order_id] = max(previous, finish) if previous else finish
            heapq.heappush(free_heap, finish)
        return ready

    def _complete_finished(self, now: datetime) -> list[BakeTask]:
        completed: list[BakeTask] = []
        for slot in self._slots:
            task = slot.task
            if task is None or task.finish_at is None or task.finish_at > now:
                continue
            task.state = TaskState.DONE
            completed.append(task)
            slot.task = None
            slot.free_at = now
        return completed

    def _fill_free_slots(self, now: datetime) -> None:
        for slot in self._slots:
            if slot.task is not None:
                continue
            if not self._queue:
                break
            _, _, task = heapq.heappop(self._queue)
            task.state = TaskState.BAKING
            task.started_at = now
            task.finish_at = now + timedelta(seconds=task.bake_seconds)
            slot.task = task
            slot.free_at = task.finish_at
