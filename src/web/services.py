from __future__ import annotations

import asyncio

from creart import it
from src.api import WebAPI
from src.config import Config
from src.flags import Flags
from src.grpc.manager import WrapperManager
from src.quality import get_available_audio_quality
from src.url import AppleMusicURL, URLType
from src.web.events import EventBus
from src.web.schemas import DownloadRequest, LogEntry, QualityItem, QualityRequest, QualityResponse, SystemStatusResponse, TaskSnapshot


class WebUIService:
    def __init__(self, event_bus: EventBus, wrapper_manager, measurer, ripper) -> None:
        self._event_bus = event_bus
        self._wrapper_manager = wrapper_manager
        self._measurer = measurer
        self._ripper = ripper
        self._current_task = TaskSnapshot()

    @property
    def wrapper_manager(self):
        return self._wrapper_manager

    @property
    def event_bus(self):
        return self._event_bus

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

    async def start_download(self, request: DownloadRequest) -> TaskSnapshot:
        parsed = AppleMusicURL.parse_url(request.url)
        if not parsed:
            raise ValueError("Invalid Apple Music URL")

        snapshot = TaskSnapshot(
            state="starting",
            url=request.url,
            codec=request.codec,
            detail=f"Preparing {parsed.type.value} task",
        )
        self.replace_current_task(snapshot)
        await self._event_bus.publish("task.state", snapshot.model_dump())

        flags = Flags(force_save=request.force, language=request.language)

        async def _run_with_error_handling(coro):
            try:
                await coro
            except Exception as exc:
                self._current_task = self._current_task.model_copy(
                    update={"state": "failed", "error": str(exc)}
                )
                await self._event_bus.publish("task.state", self._current_task.model_dump())

        if parsed.type == URLType.Song:
            asyncio.create_task(_run_with_error_handling(self._ripper.rip_song(parsed, request.codec, flags)))
        elif parsed.type == URLType.Album:
            asyncio.create_task(_run_with_error_handling(self._ripper.rip_album(parsed, request.codec, flags)))
        elif parsed.type == URLType.Artist:
            asyncio.create_task(_run_with_error_handling(self._ripper.rip_artist(parsed, request.codec, flags)))
        elif parsed.type == URLType.Playlist:
            asyncio.create_task(_run_with_error_handling(self._ripper.rip_playlist(parsed, request.codec, flags)))
        else:
            raise ValueError(f"Unsupported URLType: {parsed.type}")

        return snapshot

    async def quality_lookup(self, request: QualityRequest) -> QualityResponse:
        parsed = AppleMusicURL.parse_url(request.url)
        if not parsed:
            raise ValueError("Invalid Apple Music URL")

        async def collect_song_quality(song_id: str, storefront: str, track_label: str | None = None) -> list[QualityItem]:
            m3u8_url = await it(WrapperManager).m3u8(song_id)
            raw_items = await get_available_audio_quality(m3u8_url)
            return [
                QualityItem.model_validate({**item.model_dump(), "track_label": track_label})
                for item in raw_items
            ]

        if parsed.type == URLType.Song:
            items = await collect_song_quality(parsed.id, parsed.storefront)
            return QualityResponse(url=request.url, items=items)

        if parsed.type == URLType.Album:
            album = await it(WebAPI).get_album_info(parsed.id, parsed.storefront, it(Config).region.language)
            items: list[QualityItem] = []
            for track in album.data[0].relationships.tracks.data:
                items.extend(
                    await collect_song_quality(
                        track.id,
                        parsed.storefront,
                        f"{track.attributes.artistName} - {track.attributes.name}",
                    )
                )
            return QualityResponse(url=request.url, items=items)

        if parsed.type == URLType.Playlist:
            playlist = await it(WebAPI).get_playlist_info_and_tracks(parsed.id, parsed.storefront, it(Config).region.language)
            items: list[QualityItem] = []
            for track in playlist.data[0].relationships.tracks.data:
                items.extend(
                    await collect_song_quality(
                        track.id,
                        parsed.storefront,
                        f"{track.attributes.artistName} - {track.attributes.name}",
                    )
                )
            return QualityResponse(url=request.url, items=items)

        raise ValueError(f"Unsupported URLType: {parsed.type}")
