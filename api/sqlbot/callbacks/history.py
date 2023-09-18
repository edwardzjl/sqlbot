from typing import Any, Callable, Optional, Union
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.memory.chat_memory import BaseChatMemory
from langchain.schema import HumanMessage, AIMessage

from sqlbot.steps import IntermediateStepsStore
from sqlbot.utils import utcnow, _default_true


class PersistHistoryCallbackHandler(AsyncCallbackHandler):
    """Custom persist chat history callback.
    Used on chains, persists input and output separately on on_chain_start and on_chain_end, with extra information.
    When using this callback, you should disable save_context in Chain.prep_outputs
    """

    def __init__(
        self,
        memory: BaseChatMemory,
        steps_store: IntermediateStepsStore,
        should_persist: Callable[[dict[str, Any]], bool] = _default_true,
    ):
        self.memory = memory
        self.steps_store = steps_store
        self.should_persist = should_persist

    async def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain starts running."""
        if self.should_persist(tags):
            msg = HumanMessage(
                content=inputs[self.memory.input_key],
                additional_kwargs={"id": run_id.hex, "sent_at": utcnow().isoformat()},
            )
            self.memory.chat_memory.add_message(msg)

    async def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain ends running."""
        if self.should_persist(tags):
            msg = AIMessage(
                content=outputs[self.memory.output_key],
                additional_kwargs={"id": run_id.hex, "sent_at": utcnow().isoformat()},
            )
            self.memory.chat_memory.add_message(msg)
            if "intermediate_steps" in outputs:
                await self.steps_store.set(run_id.hex, outputs["intermediate_steps"])

    async def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain errors."""
        if self.should_persist(tags):
            msg = AIMessage(
                content=str(error),
                additional_kwargs={"id": run_id.hex, "sent_at": utcnow().isoformat()},
            )
            self.memory.chat_memory.add_message(msg)