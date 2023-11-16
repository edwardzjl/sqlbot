from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain.memory import RedisChatMessageHistory
from loguru import logger

from sqlbot.agent import SQLBotToolkit, create_sql_agent
from sqlbot.agent.prompts import AI_PREFIX, AI_SUFFIX, HUMAN_PREFIX, HUMAN_SUFFIX
from sqlbot.callbacks import (
    LCErrorCallbackHandler,
    StreamingFinalAnswerCallbackHandler,
    StreamingIntermediateThoughtCallbackHandler,
    UpdateConversationCallbackHandler,
    WebsocketHumanApprovalCallbackHandler,
)
from sqlbot.config import settings
from sqlbot.history import CustomRedisChatMessageHistory
from sqlbot.memory import FlexConversationBufferWindowMemory
from sqlbot.models import Conversation as ORMConversation
from sqlbot.schemas import (
    ChatMessage,
    Conversation,
    ConversationDetail,
    UpdateConversation,
)
from sqlbot.state import app_state
from sqlbot.utils import UserIdHeader, utcnow

router = APIRouter(
    prefix="/api",
    tags=["conversation"],
)


@router.get("/conversations", response_model=list[Conversation])
async def get_conversations(userid: Annotated[str | None, UserIdHeader()] = None):
    convs = await ORMConversation.find(ORMConversation.owner == userid).all()
    convs.sort(key=lambda x: x.updated_at, reverse=True)
    return [Conversation(**conv.dict()) for conv in convs]


# Cannot marshall response as response_model=list[tuple[AgentAction, Any]], don't know why
@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    history = RedisChatMessageHistory(
        url=str(settings.redis_om_url),
        session_id=f"{userid}:{conversation_id}",
    )
    return ConversationDetail(
        messages=[
            ChatMessage.from_lc(lc_message=message, conv_id=conversation_id, from_="ai")
            if message.type == "ai"
            else ChatMessage.from_lc(
                lc_message=message, conv_id=conversation_id, from_=userid
            )
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("/conversations", status_code=201, response_model=ConversationDetail)
async def create_conversation(userid: Annotated[str | None, UserIdHeader()] = None):
    conv = ORMConversation(title=f"New chat", owner=userid)
    await conv.save()
    return ConversationDetail(**conv.dict())


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    conv.title = payload.title
    conv.updated_at = utcnow()
    await conv.save()


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str, userid: Annotated[str | None, UserIdHeader()] = None
):
    await ORMConversation.delete(conversation_id)


@router.websocket("/chat")
async def generate(
    websocket: WebSocket,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()

    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.model_validate_json(payload)

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
                db=app_state.warehouse,
                llm=app_state.coder_llm,
                redis_url=str(settings.redis_om_url),
                conversation_id=message.conversation,
            )

            history = CustomRedisChatMessageHistory(
                url=str(settings.redis_om_url),
                session_id=f"{userid}:{message.conversation}",
            )
            memory = FlexConversationBufferWindowMemory(
                human_prefix=HUMAN_PREFIX,
                ai_prefix=AI_PREFIX,
                user_suffix=HUMAN_SUFFIX,
                ai_suffix=AI_SUFFIX,
                memory_key="history",
                chat_memory=history,
                return_messages=True,
                input_key="input",
                output_key="output",
            )

            agent_executor = create_sql_agent(
                llm=app_state.llm,
                toolkit=toolkit,
                top_k=5,
                max_iterations=10,
                input_variables=["input", "agent_scratchpad", "history"],
                agent_executor_kwargs={
                    "memory": memory,
                    "return_intermediate_steps": True,
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
                ],
            )
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {e}")
