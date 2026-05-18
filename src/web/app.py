from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.web.auth import WebAuthService
from src.web.schemas import DownloadRequest, LoginRequest, LogoutRequest, QualityRequest
from src.web.services import WebUIService


STATIC_DIR = Path(__file__).with_name("static")


def create_app(service: WebUIService) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service.attach_log_sink(asyncio.get_running_loop())
        status_task = asyncio.create_task(service.publish_system_status_loop())
        try:
            yield
        finally:
            status_task.cancel()
            with suppress(asyncio.CancelledError):
                await status_task
            service.detach_log_sink()

    app = FastAPI(title="AppleMusicDecrypt Web UI", lifespan=lifespan)
    auth = WebAuthService(service.wrapper_manager)

    @app.get("/api/system/status")
    async def get_system_status():
        return (await service.system_status()).model_dump()

    @app.get("/api/task/current")
    async def get_current_task():
        return service.current_task().model_dump()

    @app.post("/api/task/download")
    async def start_download(payload: DownloadRequest):
        try:
            snapshot = await service.start_download(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return snapshot.model_dump()

    @app.post("/api/task/retry-failed")
    async def retry_failed_tracks():
        try:
            snapshot = await service.retry_failed_tracks()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return snapshot.model_dump()

    @app.post("/api/task/quality")
    async def quality_lookup(payload: QualityRequest):
        try:
            response = await service.quality_lookup(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return response.model_dump()

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest):
        return (await auth.login(payload.username, payload.password or "", payload.two_step_code)).model_dump()

    @app.post("/api/auth/logout")
    async def logout(payload: LogoutRequest):
        return (await auth.logout(payload.username)).model_dump()

    @app.get("/api/events")
    async def events():
        async def stream():
            queue = await service.event_bus.subscribe()
            try:
                while True:
                    item = await queue.get()
                    yield f"event: {item.event}\ndata: {json.dumps({'timestamp': item.timestamp, **item.data}, ensure_ascii=False)}\n\n"
            finally:
                await service.event_bus.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app
