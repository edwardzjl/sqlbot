from typing import Any, List, Optional, Union
from uuid import UUID

from fastapi import WebSocket
from langchain.callbacks.base import AsyncCallbackHandler

from sqlbot.schemas import ChatMessage


class WebsocketCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses."""

    def __init__(self, websocket: WebSocket, conversation_id: str):
        self.websocket = websocket
        self.conversation_id = conversation_id

    async def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors."""
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=f"llm error: {str(error)}",
            type="error",
        )
        await self.websocket.send_json(message.dict())
