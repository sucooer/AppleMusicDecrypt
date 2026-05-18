from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from src.config import Notification
from src.web.schemas import TaskSnapshot


class NullNotifier:
    async def send_download_complete(self, snapshot: TaskSnapshot) -> None:
        return None

    async def send_download_failed(self, snapshot: TaskSnapshot) -> None:
        return None


class ServerChanNotifier:
    def __init__(self, config: Notification, client: Any | None = None) -> None:
        self._config = config
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(self._config.enable and self._config.serverChan3SendKey.strip())

    def _api_url(self) -> str:
        sendkey = self._config.serverChan3SendKey.strip()
        match = re.match(r"^sctp(?P<uid>\d+)t", sendkey)
        if not match:
            raise ValueError("Invalid ServerChan3 sendkey")
        return f"https://{match.group('uid')}.push.ft07.com/send/{sendkey}.send"

    def _task_name(self, snapshot: TaskSnapshot) -> str:
        return snapshot.title or snapshot.url or "未命名任务"

    def _task_type(self, snapshot: TaskSnapshot) -> str:
        task_types = {
            "song": "歌曲",
            "album": "专辑",
            "playlist": "歌单",
            "artist": "艺人",
            "music-video": "MV",
        }
        return task_types.get(snapshot.task_type or "", snapshot.task_type or "任务")

    def _base_lines(self, snapshot: TaskSnapshot) -> list[str]:
        lines = [
            f"### {self._task_name(snapshot)}",
            "",
            f"- **类型**：{self._task_type(snapshot)}",
        ]
        if snapshot.codec:
            lines.append(f"- **编码**：{snapshot.codec}")
        if snapshot.total_tracks:
            lines.append(f"- **进度**：{snapshot.completed_tracks} / {snapshot.total_tracks}")
        if snapshot.saved_path:
            lines.append(f"- **保存路径**：`{snapshot.saved_path}`")
        lines.append(f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return lines

    def _success_message(self, snapshot: TaskSnapshot) -> str:
        lines = ["## 下载完成", "", *self._base_lines(snapshot)]
        return "\n".join(lines)

    def _failure_message(self, snapshot: TaskSnapshot) -> str:
        lines = ["## 下载失败", "", *self._base_lines(snapshot)]
        if snapshot.error:
            lines.extend(["", f"> {snapshot.error}"])
        if snapshot.failed_tracks:
            lines.extend(["", "### 失败歌曲"])
            for track in snapshot.failed_tracks:
                title = track.get("title") or track.get("id") or "未知歌曲"
                error = track.get("error") or "未知错误"
                lines.append(f"- **{title}**：{error}")
        return "\n".join(lines)

    async def _send(self, title: str, desp: str, short: str) -> None:
        if not self.enabled:
            return

        payload = {
            "title": title,
            "desp": desp,
            "short": short,
            "tags": self._config.tags,
        }
        if self._client is not None:
            response = await self._client.post(self._api_url(), json=payload, timeout=10)
            response.raise_for_status()
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(self._api_url(), json=payload, timeout=10)
            response.raise_for_status()

    async def send_download_complete(self, snapshot: TaskSnapshot) -> None:
        await self._send(
            "AppleMusicDecrypt 下载完成",
            self._success_message(snapshot),
            f"{self._task_name(snapshot)} 下载完成",
        )

    async def send_download_failed(self, snapshot: TaskSnapshot) -> None:
        await self._send(
            "AppleMusicDecrypt 下载失败",
            self._failure_message(snapshot),
            f"{self._task_name(snapshot)} 下载失败",
        )
