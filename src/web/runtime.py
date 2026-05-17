from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from creart import add_creator, it

from src.api import APICreator, WebAPI
from src.config import Config, ConfigCreator
from src.grpc.manager import WMCreator, WrapperManager
from src.logger import GlobalLogger, LoggerCreator
from src.measurer import Measurer, MeasurerCreator
from src.web.events import EventBus

if TYPE_CHECKING:
    from src.rip import Ripper


@dataclass(slots=True)
class WebRuntime:
    loop: asyncio.AbstractEventLoop
    event_bus: EventBus
    logger: GlobalLogger
    config: Config
    api: WebAPI
    wrapper_manager: WrapperManager
    measurer: Measurer
    ripper: Ripper


def register_creators() -> None:
    add_creator(LoggerCreator)
    add_creator(ConfigCreator)
    add_creator(APICreator)
    add_creator(WMCreator)
    add_creator(MeasurerCreator)


async def build_runtime() -> WebRuntime:
    loop = asyncio.get_running_loop()
    event_bus = EventBus()
    it(WebAPI).init()
    await it(WrapperManager).init(it(Config).instance.url, it(Config).instance.secure)
    from src.rip import Ripper
    ripper = Ripper()
    asyncio.create_task(
        it(WrapperManager).decrypt_init(
            on_success=ripper.on_decrypt_success,
            on_failure=ripper.on_decrypt_failed,
        )
    )
    return WebRuntime(
        loop=loop,
        event_bus=event_bus,
        logger=it(GlobalLogger),
        config=it(Config),
        api=it(WebAPI),
        wrapper_manager=it(WrapperManager),
        measurer=it(Measurer),
        ripper=ripper,
    )
