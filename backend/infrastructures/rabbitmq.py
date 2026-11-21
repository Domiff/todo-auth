import asyncio
from datetime import datetime
from uuid import UUID

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from pydantic import BaseModel, ConfigDict

from backend.core.logging import get_logger
from backend.core.settings import settings

logger = get_logger(name=__name__)

connection: AbstractRobustConnection | None = None
channel: AbstractChannel | None = None
lock = asyncio.Lock()


class Event[DataT: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True)

    specversion: str
    id: UUID
    source: str
    type: str
    time: datetime
    subject: str | None = None
    datacontenttype: str
    data: DataT


async def connect() -> None:
    global connection, channel

    async with lock:
        if connection is None or connection.is_closed:
            connection = await connect_robust(url=settings.rabbitmq.url)
        if channel is None or channel.is_closed:
            channel = await connection.channel()

    logger.info("Connected to RabbitMQ")


async def disconnect() -> None:
    global connection, channel

    if connection is not None and not connection.is_closed:
        await connection.close()
    connection = channel = None

    logger.info("Disconnected from RabbitMQ")


def get_channel() -> AbstractChannel:
    if channel is None or channel.is_closed:
        raise RuntimeError("RabbitMQ is not connected")
    return channel
