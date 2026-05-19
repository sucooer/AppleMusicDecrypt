from __future__ import annotations

import asyncio
import time

from creart import it
from src.api import WebAPI
from src.config import Config
from src.flags import Flags
from src.grpc.manager import WrapperManager
from src.logger import GlobalLogger, set_log_sink
from src.quality import get_available_audio_quality
from src.url import AppleMusicURL, URLType, Song
from src.web.events import EventBus
from src.web.notifications import NullNotifier
from src.web.schemas import (
    DownloadRequest,
    LogEntry,
    QualityItem,
    QualityRequest,
    QualityResponse,
    SystemStatusResponse,
    TaskSnapshot,
    TrackSnapshot,
)


class WebUIService:
    def __init__(self, event_bus: EventBus, wrapper_manager, measurer, ripper, notifier=None) -> None:
        self._event_bus = event_bus
        self._wrapper_manager = wrapper_manager
        self._measurer = measurer
        self._ripper = ripper
        self._notifier = notifier or NullNotifier()
        self._current_task = TaskSnapshot()
        self._completion_notified = False
        self._failure_notified = False
        self._started_at = time.monotonic()

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
        self._completion_notified = False
        self._failure_notified = False
        return snapshot

    def _has_active_song_task(self, song_id: str) -> bool:
        manager = getattr(self._ripper, "download_manager", None)
        get_task = getattr(manager, "get_task", None)
        return bool(get_task(song_id)) if callable(get_task) else False

    def present_task_state(self, snapshot: TaskSnapshot | None = None) -> str:
        labels = {
            "idle": "空闲",
            "starting": "准备中",
            "fetching": "正在获取信息",
            "downloading": "正在下载",
            "decrypting": "正在解密",
            "saving": "正在保存",
            "retrying": "正在重试",
            "done": "已完成",
            "failed": "失败",
        }
        target = snapshot or self._current_task
        return labels.get(target.state, target.state)

    def present_wrapper_status(self, status: SystemStatusResponse) -> str:
        return "解密服务已连接" if status.ready else "解密服务未连接"

    async def _notify_current_task_if_needed(self) -> None:
        snapshot = self._current_task
        try:
            if snapshot.state == "done" and not self._completion_notified:
                await self._notifier.send_download_complete(snapshot)
                self._completion_notified = True
            elif (snapshot.state == "failed" or snapshot.failed_tracks) and not self._failure_notified:
                await self._notifier.send_download_failed(snapshot)
                self._failure_notified = True
        except Exception as exc:
            it(GlobalLogger).logger.warning(f"Notification failed: {exc}")

    def _track_title(self, track) -> str:
        attributes = getattr(track, "attributes", None)
        artist = getattr(attributes, "artistName", None)
        name = getattr(attributes, "name", None) or getattr(track, "id", "")
        return f"{artist} - {name}" if artist else name

    def _album_track_snapshots(self, album) -> list[TrackSnapshot]:
        tracks = album.data[0].relationships.tracks.data or []
        return [
            TrackSnapshot(id=track.id, title=self._track_title(track))
            for track in tracks
            if track.id
        ]

    def _failed_tracks(self, tracks: list[TrackSnapshot]) -> list[dict[str, str]]:
        return [
            {"id": track.id, "title": track.title, "error": track.error or "Unknown error"}
            for track in tracks
            if track.state == "failed"
        ]

    def _recount_album_progress(self, snapshot: TaskSnapshot, tracks: list[TrackSnapshot]) -> TaskSnapshot:
        completed_tracks = sum(1 for track in tracks if track.state == "done")
        failed_tracks = self._failed_tracks(tracks)
        total_tracks = snapshot.total_tracks or len(tracks)
        state = snapshot.state
        detail = snapshot.detail
        error = snapshot.error

        if total_tracks:
            detail = f"已完成 {completed_tracks} / 共 {total_tracks}"
            if failed_tracks and completed_tracks + len(failed_tracks) >= total_tracks:
                state = "failed"
                error = f"{len(failed_tracks)} 首歌曲失败"
            elif completed_tracks >= total_tracks:
                if snapshot.task_type == "album":
                    state = "saving"
                    detail = f"已完成 {completed_tracks} / 共 {total_tracks}，等待专辑任务收尾"
                else:
                    state = "done"
                    error = None
            elif state not in {"retrying", "failed"}:
                state = "downloading"

        return snapshot.model_copy(
            update={
                "state": state,
                "detail": detail,
                "error": error,
                "total_tracks": total_tracks,
                "completed_tracks": completed_tracks,
                "failed_tracks": failed_tracks,
                "tracks": tracks,
            }
        )

    def _track_state_for_log(self, entry: LogEntry) -> str | None:
        if entry.message == "Fetching metadata...":
            return "fetching"
        if entry.message == "Downloading song...":
            return "downloading"
        if entry.message.startswith("Downloading MV"):
            return "downloading"
        if entry.message == "Decrypting song...":
            return "decrypting"
        if entry.message.startswith("Decrypting MV"):
            return "decrypting"
        if entry.message == "Saving file...":
            return "saving"
        if entry.message == "Remuxing MV...":
            return "saving"
        if entry.message.startswith("Saved: ") or entry.message == "Song already exists":
            return "done"
        if entry.message == "MV already exists":
            return "done"
        if entry.level in {"ERROR", "CRITICAL"}:
            return "failed"
        return None

    def _apply_track_log(self, entry: LogEntry) -> bool:
        snapshot = self._current_task
        if snapshot.task_type != "album" or entry.item_type != "song" or not entry.item_id:
            return False

        next_track_state = self._track_state_for_log(entry)
        if not next_track_state:
            return False

        tracks = []
        found = False
        for track in snapshot.tracks:
            if track.id != entry.item_id:
                tracks.append(track)
                continue
            found = True
            title = entry.item_name or track.title
            error = entry.message if next_track_state == "failed" else None
            tracks.append(track.model_copy(update={"title": title, "state": next_track_state, "error": error}))

        if not found:
            tracks.append(
                TrackSnapshot(
                    id=entry.item_id,
                    title=entry.item_name or entry.item_id,
                    state=next_track_state,
                    error=entry.message if next_track_state == "failed" else None,
                )
            )

        saved_path = snapshot.saved_path
        if entry.message.startswith("Saved: "):
            saved_path = entry.message.removeprefix("Saved: ")

        self._current_task = self._recount_album_progress(
            snapshot.model_copy(update={"saved_path": saved_path}),
            tracks,
        )
        return True

    def attach_log_sink(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        target_loop = loop or asyncio.get_running_loop()

        def sink(payload: dict) -> None:
            entry = LogEntry.model_validate(payload)

            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is target_loop:
                asyncio.create_task(self.handle_log_event(entry))
                return

            def schedule() -> None:
                asyncio.create_task(self.handle_log_event(entry))

            target_loop.call_soon_threadsafe(schedule)

        set_log_sink(sink)

    def detach_log_sink(self) -> None:
        set_log_sink(None)

    async def system_status(self) -> SystemStatusResponse:
        status = await self._wrapper_manager.status()
        return SystemStatusResponse(
            ready=bool(getattr(status, "ready", False)),
            regions=list(getattr(status, "regions", [])),
            download_speed=self._measurer.download_speed(),
            decrypt_speed=self._measurer.decrypt_speed(),
            active_tasks=self._measurer.tasks_count(),
            server_uptime_seconds=max(0, int(time.monotonic() - self._started_at)),
        )

    async def publish_system_status(self) -> None:
        status = await self.system_status()
        await self._event_bus.publish("system.status", status.model_dump())

    async def publish_system_status_loop(self, interval: float = 1.0) -> None:
        while True:
            await self.publish_system_status()
            await asyncio.sleep(interval)

    async def append_log(self, entry: LogEntry) -> None:
        logs = [*self._current_task.logs, entry][-200:]
        self._current_task = self._current_task.model_copy(update={"logs": logs})
        await self._event_bus.publish("task.log", entry.model_dump())

    async def handle_log_event(self, entry: LogEntry) -> None:
        await self.append_log(entry)
        if self._apply_track_log(entry):
            await self._event_bus.publish("task.state", self._current_task.model_dump())
            await self._notify_current_task_if_needed()
            return

        state = self._current_task.state
        detail = self._current_task.detail
        saved_path = self._current_task.saved_path
        error = self._current_task.error

        if entry.message == "Fetching metadata...":
            state = "fetching"
            detail = entry.message
        elif entry.message == "Downloading song...":
            state = "downloading"
            detail = entry.message
        elif entry.message.startswith("Downloading MV"):
            state = "downloading"
            detail = entry.message
        elif entry.message == "Decrypting song...":
            state = "decrypting"
            detail = entry.message
        elif entry.message.startswith("Decrypting MV"):
            state = "decrypting"
            detail = entry.message
        elif entry.message == "Getting MV playlist...":
            state = "fetching"
            detail = entry.message
        elif entry.message.startswith("Selected MV"):
            detail = entry.message
        elif entry.message == "Remuxing MV...":
            state = "saving"
            detail = entry.message
        elif entry.message == "Saving file...":
            state = "saving"
            detail = entry.message
        elif entry.message.startswith("Saved: "):
            state = "done"
            detail = "Saved"
            saved_path = entry.message.removeprefix("Saved: ")
        elif entry.message == "Song already exists":
            state = "done"
            detail = entry.message
        elif entry.message == "MV already exists":
            state = "done"
            detail = entry.message
        elif entry.message == "Finished ripping":
            if self._current_task.task_type == "album" and self._current_task.failed_tracks:
                state = "failed"
                detail = self._current_task.detail
                error = self._current_task.error
            else:
                state = "done"
                detail = entry.message
        elif entry.level in {"ERROR", "CRITICAL"}:
            state = "failed"
            detail = entry.message
            error = entry.message

        self._current_task = self._current_task.model_copy(
            update={"state": state, "detail": detail, "saved_path": saved_path, "error": error}
        )
        await self._event_bus.publish("task.state", self._current_task.model_dump())
        await self._notify_current_task_if_needed()

    async def start_download(self, request: DownloadRequest) -> TaskSnapshot:
        parsed = AppleMusicURL.parse_url(request.url)
        if not parsed:
            raise ValueError("Invalid Apple Music URL")
        if parsed.type == URLType.Song and self._has_active_song_task(parsed.id):
            raise ValueError("歌曲仍在下载队列或运行中，请等待当前任务结束后再重试")

        tracks: list[TrackSnapshot] = []
        title = None
        if parsed.type == URLType.Album:
            album = await it(WebAPI).get_album_info(parsed.id, parsed.storefront, request.language)
            album_data = album.data[0]
            tracks = self._album_track_snapshots(album)
            title = self._track_title(album_data)
        elif parsed.type == URLType.MusicVideo:
            music_video = await it(WebAPI).get_music_video_info(parsed.id, parsed.storefront, request.language)
            if music_video:
                title = self._track_title(music_video)

        snapshot = TaskSnapshot(
            state="starting",
            url=request.url,
            task_type=parsed.type,
            storefront=parsed.storefront,
            title=title,
            codec=request.codec,
            language=request.language,
            force=request.force,
            detail=f"Preparing {parsed.type} task",
            total_tracks=len(tracks),
            tracks=tracks,
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
        elif parsed.type == URLType.MusicVideo:
            asyncio.create_task(_run_with_error_handling(self._ripper.rip_music_video(parsed, flags)))
        else:
            raise ValueError(f"Unsupported URLType: {parsed.type}")

        return snapshot

    async def retry_failed_tracks(self) -> TaskSnapshot:
        snapshot = self._current_task
        if snapshot.task_type != "album":
            raise ValueError("Only album tasks can retry failed tracks")

        failed_tracks = [track for track in snapshot.tracks if track.state == "failed"]
        if not failed_tracks:
            return snapshot

        tracks = [
            track.model_copy(update={"state": "pending", "error": None})
            if track.state == "failed" else track
            for track in snapshot.tracks
        ]
        self._current_task = self._recount_album_progress(
            snapshot.model_copy(
                update={
                    "state": "retrying",
                    "detail": f"正在重试 {len(failed_tracks)} 首失败歌曲",
                    "error": None,
                    "failed_tracks": [],
                    "tracks": tracks,
                }
            ),
            tracks,
        ).model_copy(update={"state": "retrying", "error": None, "failed_tracks": []})
        await self._event_bus.publish("task.state", self._current_task.model_dump())

        flags = Flags(force_save=snapshot.force, language=snapshot.language or it(Config).region.language)

        async def _retry_track(track: TrackSnapshot) -> None:
            if self._has_active_song_task(track.id):
                await self.handle_log_event(
                    LogEntry(
                        timestamp="",
                        level="ERROR",
                        source="task",
                        message="歌曲仍在下载队列或运行中，请等待当前任务结束后再重试",
                        item_type="song",
                        item_id=track.id,
                        item_name=track.title,
                    )
                )
                return

            try:
                song = Song(id=track.id, storefront=snapshot.storefront or "", url="", type=URLType.Song)
                await self._ripper.rip_song(song, snapshot.codec or "alac", flags)
            except Exception as exc:
                await self.handle_log_event(
                    LogEntry(
                        timestamp="",
                        level="ERROR",
                        source="task",
                        message=str(exc),
                        item_type="song",
                        item_id=track.id,
                        item_name=track.title,
                    )
                )

        for track in failed_tracks:
            asyncio.create_task(_retry_track(track))

        return self._current_task

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
