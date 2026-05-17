import asyncio

import uvicorn
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

from src.web.app import create_app
from src.web.runtime import build_runtime
from src.web.services import WebUIService

_runtime_app = None


async def get_app():
    global _runtime_app
    if _runtime_app is None:
        runtime = await build_runtime()
        service = WebUIService(
            event_bus=runtime.event_bus,
            wrapper_manager=runtime.wrapper_manager,
            measurer=runtime.measurer,
            ripper=runtime.ripper,
        )
        _runtime_app = create_app(service=service)
    return _runtime_app


if __name__ == "__main__":
    app = asyncio.run(get_app())
    uvicorn.run(app, host="127.0.0.1", port=8000)
