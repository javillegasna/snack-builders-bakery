import asyncio
import uuid
from collections import defaultdict
from datetime import datetime

from app.core.clock import Clock
from app.kitchen.models import BakeTask, PriorityLevel
from app.kitchen.scheduler import Scheduler
from app.kitchen.schemas import (
    KitchenStatus,
    OvenStatus,
    QueueEntryStatus,
    TrayStatus,
)

TaskSpec = tuple[PriorityLevel, int]


class KitchenEngine:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._scheduler = Scheduler()
        self._lock = asyncio.Lock()
        self._seq = 0
        self._wakeup = asyncio.Event()
        self._loop_task: asyncio.Task[None] | None = None

    async def enqueue(
        self, order_id: uuid.UUID, specs: list[TaskSpec]
    ) -> dict[uuid.UUID, datetime]:
        """Enqueue an order and return the recomputed ETA for every active order."""
        async with self._lock:
            for priority, bake_seconds in specs:
                self._scheduler.enqueue(
                    BakeTask(
                        order_id=order_id,
                        priority=priority,
                        bake_seconds=bake_seconds,
                        seq=self._seq,
                    )
                )
                self._seq += 1
            now = self._clock.now()
            self._scheduler.tick(now)
            etas = self._scheduler.estimate(now)
        self._wakeup.set()
        return etas

    async def simulate(
        self, order_id: uuid.UUID, specs: list[TaskSpec]
    ) -> datetime | None:
        """Provisional ETA for a hypothetical order. Does not mutate the queue."""
        async with self._lock:
            now = self._clock.now()
            extra = [
                BakeTask(
                    order_id=order_id,
                    priority=priority,
                    bake_seconds=bake_seconds,
                    seq=self._seq + offset,
                )
                for offset, (priority, bake_seconds) in enumerate(specs)
            ]
            return self._scheduler.simulate(now, extra).get(order_id)

    async def status(self) -> KitchenStatus:
        async with self._lock:
            return self._snapshot(self._clock.now())

    async def start(self) -> None:
        self._loop_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._loop_task is None:
            return
        self._loop_task.cancel()
        try:
            await self._loop_task
        except asyncio.CancelledError:
            pass
        self._loop_task = None

    async def _run(self) -> None:
        while True:
            async with self._lock:
                now = self._clock.now()
                self._scheduler.tick(now)
                next_finish = self._next_finish()
            timeout = None
            if next_finish is not None:
                timeout = max(0.0, (next_finish - self._clock.now()).total_seconds())
            self._wakeup.clear()
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=timeout)
            except TimeoutError:
                pass

    def _next_finish(self) -> datetime | None:
        finishes = [
            slot.task.finish_at
            for slot in self._scheduler.slots
            if slot.task is not None and slot.task.finish_at is not None
        ]
        return min(finishes) if finishes else None

    def _snapshot(self, now: datetime) -> KitchenStatus:
        trays_by_oven: dict[int, list[TrayStatus]] = defaultdict(list)
        for slot in self._scheduler.slots:
            order_id = None
            remaining = None
            if slot.task is not None and slot.task.finish_at is not None:
                order_id = slot.task.order_id
                remaining = max(0, int((slot.task.finish_at - now).total_seconds()))
            trays_by_oven[slot.oven_id].append(
                TrayStatus(
                    tray_id=slot.tray_id,
                    order_id=order_id,
                    remaining_seconds=remaining,
                )
            )
        ovens = [
            OvenStatus(oven_id=oven_id, trays=trays)
            for oven_id, trays in sorted(trays_by_oven.items())
        ]
        queue = [
            QueueEntryStatus(
                position=position,
                order_id=task.order_id,
                priority_level=int(task.priority),
            )
            for position, task in enumerate(self._scheduler.queue, start=1)
        ]
        return KitchenStatus(ovens=ovens, queue=queue)
