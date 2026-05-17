import pytest

from src.web.events import EventBus
from src.web.schemas import TaskSnapshot
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
