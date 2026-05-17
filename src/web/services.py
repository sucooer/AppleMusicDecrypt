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

    async def handle_log_event(self, entry: LogEntry) -> None:
        await self.append_log(entry)
        state = self._current_task.state
        saved_path = self._current_task.saved_path
        error = self._current_task.error

        if entry.message == "Fetching metadata...":
            state = "fetching"
        elif entry.message == "Downloading song...":
            state = "downloading"
        elif entry.message == "Decrypting song...":
            state = "decrypting"
        elif entry.message == "Saving file...":
            state = "saving"
        elif entry.message.startswith("Saved: "):
            state = "done"
            saved_path = entry.message.removeprefix("Saved: ")
        elif entry.level in {"ERROR", "CRITICAL"}:
            state = "failed"
            error = entry.message

        self._current_task = self._current_task.model_copy(
            update={"state": state, "saved_path": saved_path, "error": error}
        )
        await self._event_bus.publish("task.state", self._current_task.model_dump())
