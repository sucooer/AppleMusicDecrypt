import uvicorn

from src.web.app import create_app
from src.web.runtime import build_runtime
from src.web.services import WebUIService


async def create_runtime_app():
    runtime = await build_runtime()
    service = WebUIService(
        event_bus=runtime.event_bus,
        wrapper_manager=runtime.wrapper_manager,
        measurer=runtime.measurer,
        ripper=runtime.ripper,
    )
    return create_app(service=service)


if __name__ == "__main__":
    import asyncio

    app = asyncio.run(create_runtime_app())
    uvicorn.run(app, host="0.0.0.0", port=8000)
