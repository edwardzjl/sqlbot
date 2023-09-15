from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain.llms import HuggingFaceTextGenInference
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import MessagesPlaceholder
from langchain.sql_database import SQLDatabase
from loguru import logger

from sqlbot.agent import create_sql_agent, SQLBotToolkit
from sqlbot.agent.prompts import (
    HUMAN_PREFIX,
    AI_PREFIX,
    HUMAN_SUFFIX,
    AI_SUFFIX,
)
from sqlbot.callbacks import (
    LCErrorCallbackHandler,
    PersistHistoryCallbackHandler,
    StreamingFinalAnswerCallbackHandler,
    StreamingIntermediateThoughtCallbackHandler,
    TracingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
    WebsocketHumanApprovalCallbackHandler,
)
from sqlbot.config import settings
from sqlbot.history import AppendSuffixHistory
from sqlbot.schemas import (
    ChatMessage,
    ConversationDetail,
    Conversation,
    UpdateConversation,
)
from sqlbot.steps import IntermediateStepsStore
from sqlbot.utils import UserIdHeader, utcnow


router = APIRouter(
    prefix="/api",
    tags=["conversation"],
)

tracing_callback = TracingLLMCallbackHandler()
llm = HuggingFaceTextGenInference(
    inference_server_url=settings.isvc_llm,
    max_new_tokens=512,
    temperature=0.1,
    typical_p=None,
    stop_sequences=["</s>", "Observation", "Thought"],
    streaming=True,
    callbacks=[tracing_callback],
)

coder_llm = HuggingFaceTextGenInference(
    inference_server_url=settings.isvc_coder_llm,
    max_new_tokens=512,
    temperature=0.1,
    typical_p=None,
    stop_sequences=["</s>"],
)

history_prompt = MessagesPlaceholder(variable_name="history")

db = SQLDatabase.from_uri(settings.warehouse_url, sample_rows_in_table_info=3)

# We need to deconstruct it in app, so it must not be in the router functions
steps_store = IntermediateStepsStore(
    redis_url=settings.redis_om_url, key_prefix="sqlbot:steps"
)


@router.get("/conversations", response_model=list[Conversation])
async def get_conversations(userid: Annotated[str | None, UserIdHeader()] = None):
    convs = await Conversation.find(Conversation.owner == userid).all()
    convs.sort(key=lambda x: x.updated_at, reverse=True)
    return convs


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await Conversation.get(conversation_id)
    history = AppendSuffixHistory(
        url=settings.redis_om_url,
        user_suffix=HUMAN_SUFFIX,
        ai_suffix=AI_SUFFIX,
        session_id=f"{userid}:{conversation_id}",
    )
    return ConversationDetail(
        messages=[
            ChatMessage(
                id=UUID(message.additional_kwargs["id"]),
                conversation=conversation_id,
                from_="ai",
                content=message.content,
                type="text",
            )
            if message.type == "ai"
            else ChatMessage(
                id=UUID(message.additional_kwargs["id"]),
                conversation=conversation_id,
                from_=userid,
                content=message.content,
                type="text",
            )
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("/conversations", status_code=201, response_model=ConversationDetail)
async def create_conversation(userid: Annotated[str | None, UserIdHeader()] = None):
    conv = Conversation(title=f"New chat", owner=userid)
    await conv.save()
    return conv


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await Conversation.get(conversation_id)
    conv.title = payload.title
    conv.updated_at = utcnow()
    await conv.save()


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str, userid: Annotated[str | None, UserIdHeader()] = None
):
    await Conversation.delete(conversation_id)


@router.websocket("/chat")
async def generate(
    websocket: WebSocket,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()

    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.parse_raw(payload)

            streaming_thought_callback = StreamingIntermediateThoughtCallbackHandler(
                websocket, message.conversation
            )
            streaming_answer_callback = StreamingFinalAnswerCallbackHandler(
                websocket, message.conversation
            )
            update_conversation_callback = UpdateConversationCallbackHandler(
                message.conversation
            )
            error_callback = LCErrorCallbackHandler(websocket, message.conversation)

            def _require_approve(serialized_obj: dict) -> bool:
                # Only require approval on sql_db_query.
                return serialized_obj.get("name") == "sql_db_query"

            human_approval_callback = WebsocketHumanApprovalCallbackHandler(
                websocket, message.conversation, should_check=_require_approve
            )

            toolkit = SQLBotToolkit(
                db=db,
                llm=coder_llm,
                redis_url=settings.redis_om_url,
                conversation_id=message.conversation,
            )

            history = AppendSuffixHistory(
                url=settings.redis_om_url,
                user_suffix=HUMAN_SUFFIX,
                ai_suffix=AI_SUFFIX,
                session_id=f"{userid}:{message.conversation}",
            )
            memory = ConversationBufferWindowMemory(
                human_prefix=HUMAN_PREFIX,
                ai_prefix=AI_PREFIX,
                memory_key="history",
                chat_memory=history,
                return_messages=True,
                input_key="input",
                output_key="output",
            )

            steps_store.key_prefix = f"sqlbot:steps:{userid}:{message.conversation}"

            def _should_persist(tags: list) -> bool:
                # Only require approval on sql_db_query.
                return tags is not None and "agent_executor_chain" in tags

            history_callback = PersistHistoryCallbackHandler(
                memory=memory, steps_store=steps_store, should_persist=_should_persist
            )

            agent_executor = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                top_k=5,
                max_iterations=10,
                memory_prompts=[history_prompt],
                input_variables=["input", "agent_scratchpad", "history"],
                agent_executor_kwargs={
                    "memory": memory,
                    "return_intermediate_steps": True,
                    "tags": ["agent_executor_chain"],
                },
            )

            await agent_executor.acall(
                message.content,
                callbacks=[
                    streaming_thought_callback,
                    streaming_answer_callback,
                    update_conversation_callback,
                    error_callback,
                    human_approval_callback,
                    history_callback,
                ],
            )
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {e}")


# Cannot marshall response as response_model=list[tuple[AgentAction, Any]], don't know why
@router.get(
    "/conversations/{conversation_id}/messages/{message_id}/steps",
)
async def get_intermediate_steps(
    conversation_id: str,
    message_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    steps_store.key_prefix = f"sqlbot:steps:{userid}:{conversation_id}"
    return await steps_store.get(message_id)
