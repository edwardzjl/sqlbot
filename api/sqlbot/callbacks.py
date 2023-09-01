"""Callback handlers used in the app.
A modified version of langchain.callbacks.AsyncIteratorCallbackHandler.
"""
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import WebSocket
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.callbacks.streaming_stdout_final_only import (
    FinalStreamingStdOutCallbackHandler,
)
from langchain.schema import LLMResult

from sqlbot.schemas import ChatMessage, Conversation
from sqlbot.utils import utcnow


class StreamingLLMCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses."""

    def __init__(self, websocket: WebSocket, conversation_id: str):
        self.websocket = websocket
        self.conversation_id = conversation_id

    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
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
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=token,
            type="stream",
        )
        await self.websocket.send_json(message.dict())

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=None,
            type="end",
        )
        await self.websocket.send_json(message.dict())

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


class UpdateConversationCallbackHandler(AsyncCallbackHandler):
    def __init__(self, conversation_id: str):
        self.conversation_id: str = conversation_id

    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain ends running."""
        conv = await Conversation.get(self.conversation_id)
        conv.updated_at = utcnow()
        await conv.save()


class StreamingIntermediateThoughtCallbackHandler(AsyncCallbackHandler):
    """Streaming intermediate thought to websocket.
    Only works with agents using LLMs that support streaming.
    Only the 'thought' of the agent will be streamed.
    Must be used before the agent's output parser was called, as the output parser will likely drop the 'thought'.
    """

    def __init__(
        self,
        websocket: WebSocket,
        conversation_id: str,
        thought_prefix_tokens: list[str] = ["Th", "ought", ":"],
        strip_tokens: bool = True,
        stream_prefix: bool = False,
    ) -> None:
        """Instantiate StreamingIntermediateThoughtCallbackHandler.

        Args:
            thought_prefix_tokens: Token sequence that prefixes the thought.
                Default is ["Thought", ":"]
            strip_tokens: Ignore white spaces and new lines when comparing
                thought_prefix_tokens to last tokens? (to determine if answer has been
                reached)
            stream_prefix: Should thought prefix itself also be streamed?
        """
        super().__init__()
        self.websocket = websocket
        self.conversation_id = conversation_id
        if strip_tokens:
            self.thought_prefix_tokens = [
                token.strip() for token in thought_prefix_tokens
            ]
        else:
            self.thought_prefix_tokens = thought_prefix_tokens
        self.last_tokens = [""] * len(self.thought_prefix_tokens)
        self.strip_tokens = strip_tokens
        self.stream_prefix = stream_prefix
        self.thought_reached = False
        self.thought_ended = False

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
            if self.stream_prefix:
                for t in self.last_tokens:
                    message = ChatMessage(
                        id=run_id,
                        conversation=self.conversation_id,
                        from_="ai",
                        content=t,
                        type="stream",
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


class FinalStreamingWebsocketCallbackHandler(FinalStreamingStdOutCallbackHandler):
    def __init__(self, websocket: WebSocket, conversation_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.websocket = websocket
        self.conversation_id = conversation_id

    def append_to_last_tokens(self, token: str) -> None:
        self.last_tokens.append(token)
        if len(self.last_tokens) > len(self.answer_prefix_tokens):
            self.last_tokens.pop(0)

        stripped_token = token.strip()
        if stripped_token:
            self.last_tokens_stripped.append(token.strip())
        if len(self.last_tokens_stripped) > len(self.answer_prefix_tokens_stripped):
            self.last_tokens_stripped.pop(0)

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

        # Remember the last n tokens, where n = len(answer_prefix_tokens)
        self.append_to_last_tokens(token)

        # Check if the last n tokens match the answer_prefix_tokens list ...
        if self.check_if_answer_reached():
            self.answer_reached = True
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=None,
                type="start",
            )
            await self.websocket.send_json(message.dict())
            if self.stream_prefix:
                for t in self.last_tokens:
                    message = ChatMessage(
                        id=run_id,
                        conversation=self.conversation_id,
                        from_="ai",
                        content=t,
                        type="stream",
                    )
                    await self.websocket.send_json(message.dict())
            return

        # ... if yes, then print tokens from now on
        if self.answer_reached:
            message = ChatMessage(
                id=run_id,
                conversation=self.conversation_id,
                from_="ai",
                content=token,
                type="stream",
            )
            await self.websocket.send_json(message.dict())
