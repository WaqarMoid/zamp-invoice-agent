import asyncio
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RunEvent

logger = logging.getLogger("kestrel-ap.pipeline.events")

# In-memory broker: run_id -> set of active client queues
_SUBSCRIBERS: dict[str, set[asyncio.Queue]] = {}
_BROKER_LOCK = asyncio.Lock()


async def subscribe(run_id: str) -> asyncio.Queue:
    """Subscribe a client queue to live events for a given run_id."""
    queue: asyncio.Queue = asyncio.Queue()
    async with _BROKER_LOCK:
        if run_id not in _SUBSCRIBERS:
            _SUBSCRIBERS[run_id] = set()
        _SUBSCRIBERS[run_id].add(queue)
    return queue


async def unsubscribe(run_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe a client queue."""
    async with _BROKER_LOCK:
        if run_id in _SUBSCRIBERS:
            _SUBSCRIBERS[run_id].discard(queue)
            if not _SUBSCRIBERS[run_id]:
                del _SUBSCRIBERS[run_id]


def emit_event(
    session: Session,
    run_id: str,
    event_type: str,
    data: dict[str, Any],
) -> RunEvent:
    """
    Persist an event to run_events and broadcast to in-memory queues per doc 08 §8.3.
    """
    # 1. Determine next seq number
    stmt = select(func.coalesce(func.max(RunEvent.seq), 0)).where(RunEvent.run_id == run_id)
    current_max = session.execute(stmt).scalar() or 0
    next_seq = current_max + 1

    # 2. Persist to DB
    evt = RunEvent(
        run_id=run_id,
        seq=next_seq,
        type=event_type,
        payload=data,
    )
    session.add(evt)
    session.flush()

    # 3. Broadcast to in-memory queues
    queues = _SUBSCRIBERS.get(run_id, set()).copy()
    payload_tuple = (next_seq, event_type, data)
    for q in queues:
        try:
            q.put_nowait(payload_tuple)
        except Exception as e:
            logger.warning("Failed to put event into queue for run %s: %s", run_id, e)

    return evt
