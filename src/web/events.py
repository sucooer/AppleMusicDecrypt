from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class UIEvent:
    event: str
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[UIEvent]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[UIEvent]:
        queue: asyncio.Queue[UIEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[UIEvent]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, event: str, data: dict[str, Any]) -> UIEvent:
        payload = UIEvent(event=event, data=data)
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            await queue.put(payload)
        return payload
