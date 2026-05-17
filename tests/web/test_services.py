import asyncio

import pytest

from src.web.events import EventBus
from src.web.schemas import LogEntry, TaskSnapshot
from src.web.services import WebUIService


class FakeStatus:
    def __init__(self, ready=True, regions=None):
        self.ready = ready
        self.regions = regions or ["JP"]


class FakeWrapperManager:
    async def status(self):
        return FakeStatus()


class FakeMeasurer:
    def download_speed(self):
        return "1.00 MB/s"

    def decrypt_speed(self):
        return "2.00 MB/s"

    def tasks_count(self):
        return 1


def test_service_exposes_idle_snapshot_by_default():
    service = WebUIService(
        event_bus=EventBus(),
        wrapper_manager=FakeWrapperManager(),
        measurer=FakeMeasurer(),
        ripper=None,
    )

    assert service.current_task().state == "idle"


@pytest.mark.asyncio
async def test_service_returns_system_status_snapshot():
    service = WebUIService(
        event_bus=EventBus(),
        wrapper_manager=FakeWrapperManager(),
        measurer=FakeMeasurer(),
        ripper=None,
    )

    status = await service.system_status()

    assert status.ready is True
    assert status.regions == ["JP"]
    assert status.download_speed == "1.00 MB/s"
    assert status.decrypt_speed == "2.00 MB/s"
    assert status.active_tasks == 1


def test_service_can_replace_current_task_snapshot():
    service = WebUIService(
        event_bus=EventBus(),
        wrapper_manager=FakeWrapperManager(),
        measurer=FakeMeasurer(),
        ripper=None,
    )

    service.replace_current_task(TaskSnapshot(state="starting", url="https://example.com"))

    assert service.current_task().state == "starting"


@pytest.mark.asyncio
async def test_log_messages_drive_task_state_transitions():
    service = WebUIService(EventBus(), FakeWrapperManager(), FakeMeasurer(), ripper=None)

    await service.handle_log_event(LogEntry(timestamp="t", level="INFO", source="task", message="Fetching metadata..."))
    assert service.current_task().state == "fetching"

    await service.handle_log_event(LogEntry(timestamp="t", level="INFO", source="task", message="Downloading song..."))
    assert service.current_task().state == "downloading"

    await service.handle_log_event(LogEntry(timestamp="t", level="INFO", source="task", message="Saving file..."))
    assert service.current_task().state == "saving"

    await service.handle_log_event(LogEntry(timestamp="t", level="SUCCESS", source="task", message="Saved: /tmp/out.m4a"))
    assert service.current_task().state == "done"
    assert service.current_task().saved_path == "/tmp/out.m4a"
