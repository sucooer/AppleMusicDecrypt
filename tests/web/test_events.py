import asyncio

import pytest

from src.web.events import EventBus


@pytest.mark.asyncio
async def test_event_bus_broadcasts_to_all_subscribers():
    bus = EventBus()
    queue_a = await bus.subscribe()
    queue_b = await bus.subscribe()

    await bus.publish("task.log", {"message": "hello"})

    event_a = await asyncio.wait_for(queue_a.get(), timeout=0.2)
    event_b = await asyncio.wait_for(queue_b.get(), timeout=0.2)

    assert event_a.event == "task.log"
    assert event_a.data == {"message": "hello"}
    assert event_b.event == "task.log"
    assert event_b.data == {"message": "hello"}


@pytest.mark.asyncio
async def test_event_bus_unsubscribe_stops_future_delivery():
    bus = EventBus()
    queue = await bus.subscribe()
    await bus.unsubscribe(queue)

    await bus.publish("system.status", {"ready": True})

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.05)
