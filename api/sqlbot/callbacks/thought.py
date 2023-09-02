from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket

from sqlbot.callbacks.base import WebsocketCallbackHandler
from sqlbot.schemas import ChatMessage

DEFAULT_THOUGHT_SUFFIX_TOKENS = "Action"


class StreamingIntermediateThoughtCallbackHandler(WebsocketCallbackHandler):
    """Streaming intermediate thought to websocket.
    Typically, during agent execution, the initial messages represent intermediate thoughts, which are followed by an "action."
    This callback handler streams every token up to the "Action" to the websocket.
    It's important to note that certain formatting instructions may also stream a 'Thought:' in the initial round.
    """

    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: str,
        thought_suffix_token: Optional[str] = None,
    ) -> None:
        """Instantiate StreamingIntermediateThoughtCallbackHandler.

        Args:
            thought_prefix_tokens: Token sequence that prefixes the thought.
                Default is ["Thought", ":"]
            strip_tokens: Ignore white spaces and new lines when comparing
                thought_prefix_tokens to last tokens? (to determine if answer has been
                reached)
        """
        super().__init__(websocket, conversation_id)
        if thought_suffix_token is None:
            self.thought_suffix_token = DEFAULT_THOUGHT_SUFFIX_TOKENS
        else:
            self.thought_suffix_token = thought_suffix_token

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM starts running."""
        self.thinking = True
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=None,
            type="start",
        )
        await self.websocket.send_json(message.dict())

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        if token == self.thought_suffix_token:
            self.thinking = False

        if not self.thinking:
            return

        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=token,
            type="stream",
        )
        await self.websocket.send_json(message.dict())
