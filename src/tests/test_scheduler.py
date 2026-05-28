import uuid
from datetime import UTC, datetime

from app.kitchen.models import SLOT_COUNT, BakeTask, PriorityLevel, TaskState
from app.kitchen.scheduler import Scheduler

COOKIE = 300
PASTRY = 600
BREAD = 1200
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_task(
    seq: int,
    priority: PriorityLevel = PriorityLevel.WALK_IN,
    bake_seconds: int = COOKIE,
    order_id: uuid.UUID | None = None,
) -> BakeTask:
    return BakeTask(
        order_id=order_id or uuid.uuid4(),
        priority=priority,
        bake_seconds=bake_seconds,
        seq=seq,
    )


def busy_tasks(scheduler: Scheduler) -> list[BakeTask]:
    return [slot.task for slot in scheduler.slots if slot.task is not None]


def test_six_slots() -> None:
    assert len(Scheduler().slots) == SLOT_COUNT == 6


def test_seven_cookies_fill_six_one_waits() -> None:
    scheduler = Scheduler()
    for seq in range(7):
        scheduler.enqueue(make_task(seq))
    scheduler.tick(NOW)
    assert len(busy_tasks(scheduler)) == 6
    assert all(t.state is TaskState.BAKING for t in busy_tasks(scheduler))
    assert len(scheduler.queue) == 1


def test_capacity_never_exceeded() -> None:
    scheduler = Scheduler()
    for seq in range(20):
        scheduler.enqueue(make_task(seq))
    scheduler.tick(NOW)
    assert len(busy_tasks(scheduler)) <= SLOT_COUNT


def test_completion_frees_slot_and_pulls_next() -> None:
    scheduler = Scheduler()
    for seq in range(7):
        scheduler.enqueue(make_task(seq))
    scheduler.tick(NOW)
    later = NOW.replace(minute=5)
    completed = scheduler.tick(later)
    assert len(completed) == 6
    assert all(t.state is TaskState.DONE for t in completed)
    assert len(busy_tasks(scheduler)) == 1
    assert len(scheduler.queue) == 0


def test_priority_vip_jumps_waiting_queue() -> None:
    scheduler = Scheduler()
    for seq in range(6):
        scheduler.enqueue(make_task(seq, PriorityLevel.WALK_IN))
    vip = make_task(6, PriorityLevel.VIP)
    scheduler.enqueue(vip)
    scheduler.tick(NOW)
    assert vip in busy_tasks(scheduler)
    assert len(scheduler.queue) == 1
    assert scheduler.queue[0].priority is PriorityLevel.WALK_IN


def test_no_preemption_baking_tasks_untouched() -> None:
    scheduler = Scheduler()
    walk_ins = [make_task(seq, PriorityLevel.WALK_IN) for seq in range(6)]
    for task in walk_ins:
        scheduler.enqueue(task)
    scheduler.tick(NOW)
    baking_ids = {t.id for t in busy_tasks(scheduler)}
    scheduler.enqueue(make_task(6, PriorityLevel.VIP))
    scheduler.tick(NOW)
    assert {t.id for t in busy_tasks(scheduler)} == baking_ids
    assert scheduler.queue[0].priority is PriorityLevel.VIP


def test_fifo_within_same_tier() -> None:
    scheduler = Scheduler()
    for seq in (2, 0, 1):
        scheduler.enqueue(make_task(seq, PriorityLevel.WALK_IN))
    assert [t.seq for t in scheduler.queue] == [0, 1, 2]


def test_estimate_seventh_cookie_ready_after_two_batches() -> None:
    scheduler = Scheduler()
    last_order = uuid.uuid4()
    for seq in range(6):
        scheduler.enqueue(make_task(seq))
    scheduler.enqueue(make_task(6, order_id=last_order))
    ready = scheduler.estimate(NOW)
    assert (ready[last_order] - NOW).total_seconds() == 2 * COOKIE


def test_estimate_accounts_for_baking_slots() -> None:
    scheduler = Scheduler()
    baking_order = uuid.uuid4()
    scheduler.enqueue(make_task(0, bake_seconds=BREAD, order_id=baking_order))
    scheduler.tick(NOW)
    ready = scheduler.estimate(NOW)
    assert (ready[baking_order] - NOW).total_seconds() == BREAD


def test_estimate_vip_ready_before_lower_priority() -> None:
    scheduler = Scheduler()
    vip_order = uuid.uuid4()
    walk_order = uuid.uuid4()
    for seq in range(6):
        scheduler.enqueue(make_task(seq, PriorityLevel.WALK_IN))
    scheduler.enqueue(make_task(6, PriorityLevel.WALK_IN, order_id=walk_order))
    scheduler.enqueue(make_task(7, PriorityLevel.VIP, order_id=vip_order))
    ready = scheduler.estimate(NOW)
    assert ready[vip_order] < ready[walk_order]
