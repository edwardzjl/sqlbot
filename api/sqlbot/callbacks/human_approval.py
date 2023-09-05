from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import WebSocket
import sqlparse

# from langchain.callbacks.human import HumanApprovalCallbackHandler

from sqlbot.callbacks.base import WebsocketCallbackHandler
from sqlbot.schemas import ChatMessage


def _default_true(_: dict[str, Any]) -> bool:
    return True


class WebsocketHumanApprovalCallbackHandler(WebsocketCallbackHandler):
    """TODO: make a real human approval callback handler."""

    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: str,
        should_check: Callable[[dict[str, Any]], bool] = _default_true,
    ):
        super().__init__(websocket, conversation_id)
        self._should_check = should_check

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool starts running."""
        if self._should_check(serialized):
            formated_sql = sqlparse.format(
                input_str, reindent=True, keyword_case="upper"
            )
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=f"executing sql:\n```sql\n{formated_sql}\n```",
                type="text",
            )
            await self.websocket.send_json(message.dict())
