from typing import Any

from fastapi import HTTPException
from langchain.schema import AgentAction
from loguru import logger
from pydantic import BaseModel
from redis.asyncio import Redis


class IntermediateSteps(BaseModel):
    """Used to serialize list of pydantic models."""

    __root__: list[tuple[AgentAction, Any]]


class IntermediateStepsStore:
    def __init__(self, redis_url, key_prefix):
        self.connection = Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
        logger.info("intermediate steps store initialized")

    async def get(self, key: str) -> list[tuple[AgentAction, Any]]:
        value = await self.connection.get(f"{self.key_prefix}:{key}")
        if value is None:
            raise HTTPException(status_code=404, detail="Intermediate steps not found")
        wrap = IntermediateSteps.parse_raw(value)
        return wrap.__root__

    async def set(self, key: str, value: list[tuple[AgentAction, Any]]) -> None:
        wrap = IntermediateSteps(__root__=value)
        await self.connection.set(f"{self.key_prefix}:{key}", wrap.json())

    async def close(self):
        await self.connection.close()
        logger.info("intermediate steps store closed")
