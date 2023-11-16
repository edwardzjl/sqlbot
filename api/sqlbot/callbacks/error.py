from typing import Any, Optional
from uuid import UUID

from sqlbot.callbacks.base import WebsocketCallbackHandler
from sqlbot.schemas import ChatMessage


class LCErrorCallbackHandler(WebsocketCallbackHandler):
    async def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
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
        await self.websocket.send_text(message.model_dump_json())

    async def on_chain_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain errors."""
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=f"chain error: {str(error)}",
            type="error",
        )
        await self.websocket.send_text(message.model_dump_json())

    async def on_tool_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool errors."""
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=f"tool error: {str(error)}",
            type="error",
        )
        await self.websocket.send_text(message.model_dump_json())

    async def on_retriever_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on retriever error."""
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=f"retriever error: {str(error)}",
            type="error",
        )
        await self.websocket.send_text(message.model_dump_json())
