from __future__ import annotations

from src.web.events import EventBus
from src.web.schemas import LogEntry, SystemStatusResponse, TaskSnapshot


class WebUIService:
    def __init__(self, event_bus: EventBus, wrapper_manager, measurer, ripper) -> None:
        self._event_bus = event_bus
        self._wrapper_manager = wrapper_manager
        self._measurer = measurer
        self._ripper = ripper
        self._current_task = TaskSnapshot()

    def current_task(self) -> TaskSnapshot:
        return self._current_task

    def replace_current_task(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        self._current_task = snapshot
        return snapshot

    async def system_status(self) -> SystemStatusResponse:
        status = await self._wrapper_manager.status()
        return SystemStatusResponse(
            ready=bool(getattr(status, "ready", False)),
            regions=list(getattr(status, "regions", [])),
            download_speed=self._measurer.download_speed(),
            decrypt_speed=self._measurer.decrypt_speed(),
            active_tasks=self._measurer.tasks_count(),
        )

    async def append_log(self, entry: LogEntry) -> None:
        logs = [*self._current_task.logs, entry][-200:]
        self._current_task = self._current_task.model_copy(update={"logs": logs})
        await self._event_bus.publish("task.log", entry.model_dump())
