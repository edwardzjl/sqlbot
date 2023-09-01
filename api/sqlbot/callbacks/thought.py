from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket

from sqlbot.callbacks.base import WebsocketCallbackHandler
from sqlbot.schemas import ChatMessage

DEFAULT_THOUGHT_PREFIX_TOKENS = ["Th", "ought", ":"]


class StreamingIntermediateThoughtCallbackHandler(WebsocketCallbackHandler):
    """Streaming intermediate thought to websocket.
    Based on `langchain.callbacks.streaming_stdout_final_only.FinalStreamingStdOutCallbackHandler`
    """

    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: str,
        thought_prefix_tokens: Optional[list[str]] = None,
        strip_tokens: bool = True,
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
        if thought_prefix_tokens is None:
            self.thought_prefix_tokens = DEFAULT_THOUGHT_PREFIX_TOKENS
        else:
            self.thought_prefix_tokens = thought_prefix_tokens
        if strip_tokens:
            self.thought_prefix_tokens = [
                token.strip() for token in self.thought_prefix_tokens
            ]
        self.strip_tokens = strip_tokens

    def check_if_thought_reached(self) -> bool:
        return self.last_tokens == self.thought_prefix_tokens

    def append_to_last_tokens(self, token: str) -> None:
        if self.strip_tokens:
            token = token.strip()
            if token:
                self.last_tokens.append(token)
        else:
            self.last_tokens.append(token)
        if len(self.last_tokens) > len(self.thought_prefix_tokens):
            self.last_tokens.pop(0)

    async def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.last_tokens = [""] * len(self.thought_prefix_tokens)
        self.thought_reached = False
        self.thought_ended = False

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
        if token == "Action":
            self.thought_ended = True

        if self.thought_ended:
            return

        # Remember the last n tokens, where n = len(answer_prefix_tokens)
        self.append_to_last_tokens(token)

        # Check if the last n tokens match the answer_prefix_tokens list ...
        if self.check_if_thought_reached():
            self.thought_reached = True
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=None,
                type="start",
            )
            await self.websocket.send_json(message.dict())
            return

        # ... if yes, then print tokens from now on
        if self.thought_reached:
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=token,
                type="stream",
            )
            await self.websocket.send_json(message.dict())
