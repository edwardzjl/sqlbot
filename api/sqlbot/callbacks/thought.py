from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket

from sqlbot.callbacks.base import WebsocketCallbackHandler
from sqlbot.schemas import ChatMessage

DEFAULT_ACTION_PREFFIX_TOKEN = "Action"
DEFAULT_ANSWER_PREFIX_TOKENS = ["Final", " Answer", ":"]


class StreamingIntermediateThoughtCallbackHandler(WebsocketCallbackHandler):
    """Streaming intermediate thought to websocket.
    Typically, during agent execution, the initial messages represent intermediate thoughts, which are followed by an "action."
    This callback handler streams every token up to the "Action" or "Final Answer" to the websocket.
    """

    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: str,
        action_preffix_token: Optional[str] = None,
        answer_prefix_tokens: Optional[list[str]] = None,
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
        if action_preffix_token is None:
            self.action_preffix_token = DEFAULT_ACTION_PREFFIX_TOKEN
        else:
            self.action_preffix_token = action_preffix_token
        if answer_prefix_tokens is None:
            self.answer_prefix_tokens = DEFAULT_ANSWER_PREFIX_TOKENS
        else:
            self.answer_prefix_tokens = answer_prefix_tokens

    def append_to_last_tokens(self, token: str) -> None:
        # we cannot strip the token here, as we need to stream out from self.last_tokens
        self.last_tokens.append(token)
        if len(self.last_tokens) > len(self.answer_prefix_tokens):
            self.last_tokens.pop(0)

    def answer_reached(self) -> bool:
        return self.last_tokens == self.answer_prefix_tokens

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
        self.last_tokens = [""] * len(self.answer_prefix_tokens)
        self.thinking = True
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=None,
            type="thought/start",
        )
        await self.websocket.send_text(message.model_dump_json())

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
        if not self.thinking:
            return

        if token == self.action_preffix_token:
            self.thinking = False
            # stream out the last n tokens
            for t in self.last_tokens[1:]:
                message = ChatMessage(
                    id=run_id,
                    conversation=self.conversation_id,
                    from_="ai",
                    content=t,
                    type="thought/text",
                )
                await self.websocket.send_text(message.model_dump_json())
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=None,
                type="thought/end",
            )
            await self.websocket.send_text(message.model_dump_json())
            return

        self.append_to_last_tokens(token)
        if self.answer_reached():
            self.thinking = False
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=None,
                type="thought/end",
            )
            await self.websocket.send_text(message.model_dump_json())
            return

        if "" in self.last_tokens:
            # self.last_tokens is not full yet, we cannot deside whether the answer is reached
            return

        # self.last_tokens is full, but the answer is not reached. Stream out the first token
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=self.last_tokens[0],
            type="thought/text",
        )
        await self.websocket.send_text(message.model_dump_json())
