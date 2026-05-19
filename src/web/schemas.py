from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TaskState = Literal[
    "idle",
    "starting",
    "fetching",
    "downloading",
    "decrypting",
    "saving",
    "retrying",
    "done",
    "failed",
]

TrackState = Literal[
    "pending",
    "fetching",
    "downloading",
    "decrypting",
    "saving",
    "done",
    "failed",
]


class LogEntry(BaseModel):
    timestamp: str
    level: str
    source: Literal["system", "task"]
    message: str
    item_type: str | None = None
    item_id: str | None = None
    item_name: str | None = None


class DownloadRequest(BaseModel):
    url: str
    codec: str = "alac"
    language: str = "zh-Hans-CN"
    force: bool = False

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("url must not be blank")
        return value


class QualityRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("url must not be blank")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str | None = None
    two_step_code: str | None = None


class LogoutRequest(BaseModel):
    username: str


class TrackSnapshot(BaseModel):
    id: str
    title: str
    state: TrackState = "pending"
    error: str | None = None


class TaskSnapshot(BaseModel):
    state: TaskState = "idle"
    url: str | None = None
    task_type: str | None = None
    storefront: str | None = None
    title: str | None = None
    detail: str | None = None
    codec: str | None = None
    language: str | None = None
    force: bool = False
    saved_path: str | None = None
    error: str | None = None
    total_tracks: int = 0
    completed_tracks: int = 0
    failed_tracks: list[dict[str, str]] = Field(default_factory=list)
    tracks: list[TrackSnapshot] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)


class QualityItem(BaseModel):
    track_label: str | None = None
    codec_id: str
    codec: str
    bitrate: int
    average_bitrate: int | None = None
    channels: str | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None


class QualityResponse(BaseModel):
    url: str
    items: list[QualityItem]


class SystemStatusResponse(BaseModel):
    ready: bool
    regions: list[str]
    download_speed: str
    decrypt_speed: str
    active_tasks: int
    server_uptime_seconds: int = 0


class AuthResponse(BaseModel):
    status: Literal["success", "need_2fa", "failed"]
    message: str


class EventEnvelope(BaseModel):
    event: str
    data: dict[str, Any]
    timestamp: str
