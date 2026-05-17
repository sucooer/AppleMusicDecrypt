from creart import add_creator

from src.config import ConfigCreator
add_creator(ConfigCreator)

from src.logger import LoggerCreator
add_creator(LoggerCreator)

from src.api import APICreator
add_creator(APICreator)

from src.grpc.manager import WMCreator
add_creator(WMCreator)

from src.measurer import MeasurerCreator
add_creator(MeasurerCreator)

from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.events import EventBus
from src.web.schemas import QualityResponse, SystemStatusResponse, TaskSnapshot
from src.web.services import WebUIService


class FakeWrapperManager:
    async def status(self):
        class Status:
            ready = True
            regions = ["JP"]
        return Status()


class FakeMeasurer:
    def download_speed(self):
        return "0.00 kB/s"

    def decrypt_speed(self):
        return "0.00 kB/s"

    def tasks_count(self):
        return 0


class FakeRipper:
    pass


def build_service():
    return WebUIService(EventBus(), FakeWrapperManager(), FakeMeasurer(), FakeRipper())


def test_system_status_endpoint_returns_snapshot():
    app = create_app(service=build_service())
    client = TestClient(app)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["regions"] == ["JP"]


def test_current_task_endpoint_returns_idle_snapshot():
    app = create_app(service=build_service())
    client = TestClient(app)

    response = client.get("/api/task/current")

    assert response.status_code == 200
    assert response.json()["state"] == "idle"


def test_download_endpoint_rejects_blank_url():
    app = create_app(service=build_service())
    client = TestClient(app)

    response = client.post("/api/task/download", json={"url": "   "})

    assert response.status_code == 422
