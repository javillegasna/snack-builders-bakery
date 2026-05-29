import asyncio
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import Clock
from app.kitchen.models import BakeTask, PriorityLevel, TaskState
from app.kitchen.scheduler import Scheduler
from app.kitchen.schemas import (
    KitchenStatus,
    OvenStatus,
    QueueEntryStatus,
    TrayStatus,
)
from app.orders.models import OrderStatus
from app.orders.repository import OrderRepository

TaskSpec = tuple[PriorityLevel, int]

RECONCILE_SECONDS = 5.0

_STATUS_RANK = {OrderStatus.QUEUED: 0, OrderStatus.BAKING: 1, OrderStatus.READY: 2}


class KitchenEngine:
    def __init__(
        self,
        clock: Clock,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._clock = clock
        self._scheduler = Scheduler()
        self._lock = asyncio.Lock()
        self._seq = 0
        self._wakeup = asyncio.Event()
        self._loop_task: asyncio.Task[None] | None = None
        self._session_factory = session_factory
        self._remaining: dict[uuid.UUID, int] = {}
        self._ready_at: dict[uuid.UUID, datetime] = {}
        self._persisted: dict[uuid.UUID, OrderStatus] = {}

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
            self._remaining[order_id] = self._remaining.get(order_id, 0) + len(specs)
            now = self._clock.now()
            self._account(self._scheduler.tick(now), now)
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
            await self._reconcile()
            async with self._lock:
                next_finish = self._next_finish()
            timeout = None
            if next_finish is not None:
                timeout = max(0.0, (next_finish - self._clock.now()).total_seconds())
            if self._session_factory is not None:
                timeout = (
                    RECONCILE_SECONDS
                    if timeout is None
                    else min(timeout, RECONCILE_SECONDS)
                )
            self._wakeup.clear()
            try:
                await asyncio.wait_for(self._wakeup.wait(), timeout=timeout)
            except TimeoutError:
                pass

    async def _reconcile(self) -> None:
        async with self._lock:
            now = self._clock.now()
            self._account(self._scheduler.tick(now), now)
            transitions = self._pending_transitions()
        await self._persist(transitions)

    def _account(self, completed: list[BakeTask], now: datetime) -> None:
        for task in completed:
            remaining = self._remaining.get(task.order_id)
            if remaining is None:
                continue
            remaining -= 1
            if remaining <= 0:
                self._remaining.pop(task.order_id, None)
                self._ready_at[task.order_id] = now
            else:
                self._remaining[task.order_id] = remaining

    def _pending_transitions(self) -> list[tuple[uuid.UUID, OrderStatus, datetime]]:
        desired: dict[uuid.UUID, tuple[OrderStatus, datetime]] = {}
        for slot in self._scheduler.slots:
            task = slot.task
            if task is not None and task.state is TaskState.BAKING:
                started = task.started_at
                if started is None:
                    continue
                current = desired.get(task.order_id)
                if current is None or started < current[1]:
                    desired[task.order_id] = (OrderStatus.BAKING, started)
        for order_id, ready_at in self._ready_at.items():
            desired[order_id] = (OrderStatus.READY, ready_at)
        out: list[tuple[uuid.UUID, OrderStatus, datetime]] = []
        for order_id, (status, at) in desired.items():
            seen = self._persisted.get(order_id)
            if seen is None or _STATUS_RANK[seen] < _STATUS_RANK[status]:
                out.append((order_id, status, at))
        return out

    async def _persist(
        self, transitions: list[tuple[uuid.UUID, OrderStatus, datetime]]
    ) -> None:
        if not transitions or self._session_factory is None:
            return
        changed: list[tuple[uuid.UUID, OrderStatus]] = []
        async with self._session_factory() as session:
            orders = OrderRepository(session)
            for order_id, status, at in transitions:
                if await orders.advance_status(order_id, status, at):
                    changed.append((order_id, status))
            await session.commit()
        for order_id, status in changed:
            self._persisted[order_id] = status

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
