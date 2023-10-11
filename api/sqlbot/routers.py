from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain.llms import HuggingFaceTextGenInference
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import MessagesPlaceholder
from langchain.vectorstores.redis import Redis, RedisText
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
from sqlbot.vector_store.service import embeddings
from sqlbot.config import settings
from sqlbot.history import AppendSuffixHistory
from sqlbot.models import Conversation as ORMConversation
from sqlbot.schemas import (
    ChatMessage,
    ConversationDetail,
    Conversation,
    UpdateConversation,
)
from sqlbot.utils import UserIdHeader, utcnow
from sqlbot.vector_store import append_vector_store_sql, store_vector_store_sql


router = APIRouter(
    prefix="/api",
    tags=["conversation"],
)

tracing_callback = TracingLLMCallbackHandler()
llm = HuggingFaceTextGenInference(
    inference_server_url=str(settings.isvc_llm),
    max_new_tokens=512,
    temperature=0.1,
    typical_p=None,
    stop_sequences=["</s>", "Observation", "Thought"],
    streaming=True,
    callbacks=[tracing_callback],
)

coder_llm = HuggingFaceTextGenInference(
    inference_server_url=str(settings.isvc_coder_llm),
    max_new_tokens=512,
    temperature=0.1,
    typical_p=None,
    stop_sequences=["</s>"],
)

history_prompt = MessagesPlaceholder(variable_name="history")

db = SQLDatabase.from_uri(str(settings.warehouse_url), sample_rows_in_table_info=3)


@router.post("/{conversation_id}/init", status_code=201)
async def init_vector_store(
    conversation_id: str,
    payload: dict,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    vector_store = store_vector_store_sql(
        chat_id=conversation_id,
        user_id=userid,
        query_payload=payload,
    )


@router.put("/{conversation_id}", status_code=201)
async def update_vector_store(
    conversation_id: str,
    payload: dict,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    append_vector_store_sql(
        chat_id=conversation_id,
        user_id=userid,
        payload=payload,
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
    history = AppendSuffixHistory(
        url=str(settings.redis_om_url),
        user_suffix=HUMAN_SUFFIX,
        ai_suffix=AI_SUFFIX,
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
    conversation_detail = ConversationDetail(**conv.dict())
    relationship_payload = {
        "演员-角色": "select * from actors a join roles r on a.id = r.actor_id",
        "导演-电影类型": "select * from directors d join directors_genres dr on d.id = dr.director_id",
        "导演-电影": "select * from directors d join movies_directors md on d.id = md.director_id",
        "电影-电影类型": "select * from movies m join movies_genres mg on m.id = mg.movie_id",
        "电影-角色": "select * from movies m join roles r on m.id = r.movie_id",
    }
    query_payload = {
        "排名前10的电影名称和年份": "SELECT name, YEAR from movies ORDER BY movies.rank DESC LIMIT 10;",
        "总共有多少部电影？": "SELECT COUNT(*) FROM movies;",
        "$1,000,000 Duck是什么类型的电影?": "select mg.genre from movies m join movies_genres mg on m.id = mg.movie_id where m.name ='$1,000,000 Duck'",
        "找出导演表中共有多少不同的导演": "SELECT COUNT(DISTINCT id) FROM directors;",
        "查找电影'$ucces Part One'的类型": "SELECT mov.name, mg.genre FROM movies_genres mg inner join movies mov on mg.movie_id = mov.id WHERE mov.name = '$ucces Part One';",
        "找出导演Khairiya执导的电影列表": "SELECT m.name FROM movies_directors md JOIN movies m ON md.movie_id = m.id WHERE md.director_id = (SELECT id FROM directors WHERE first_name = 'Khairiya' AND last_name = '');",
        "找出出演最多电影角色的演员": "SELECT actors.id, actors.first_name, actors.last_name, COUNT(DISTINCT roles.movie_id) AS num_movies FROM actors LEFT JOIN ROLES ON actors.id = roles.actor_id GROUP BY actors.id, actors.first_name, actors.last_name ORDER BY num_movies DESC LIMIT 1;",
        "找出导演表中拥有最多执导电影的导演名字": 'SELECT d.first_name || \' \' || d.last_name AS "导演名字" FROM directors d JOIN movies_directors md ON d.id = md.director_id GROUP BY "导演名字" ORDER BY COUNT(md.movie_id) DESC LIMIT 1;',
        "列出演员表中的不同性别以及每种性别的演员数量": 'SELECT gender, COUNT(*) AS "演员数量" FROM actors GROUP BY gender;',
        "列出电影表中的不同年份和每年的电影数量": 'SELECT year, COUNT(*) AS "电影数量" FROM movies GROUP BY year ORDER BY year;',
        "名为'Christopher'的导演的姓什么": "SELECT last_name FROM directors WHERE first_name = 'Christopher';",
        "列出导演拍过的电影类型及其占比，按占比降序排序": "SELECT ds.first_name, genre, prob FROM directors_genres dg inner join directors ds on dg.director_id = ds.id ORDER BY prob DESC;",
        "Candy Chan演过多少电影?": "select count(*) from roles r join movies m on r.movie_id =m.id where r.actor_id = (SELECT id FROM actors a WHERE a.first_name = 'Candy' AND a.last_name = 'Chan');",
    }
    store_vector_store_sql(
        chat_id=conversation_detail.id,
        user_id=userid,
        query_payload=query_payload,
        relationship_payload=relationship_payload,
    )
    return conversation_detail


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
            vector_store = Redis.from_existing_index(
                redis_url="redis://localhost:6379/0",
                embedding=embeddings,
                index_name=f"{userid}:{message.conversation}",
                schema="redis_schema.yaml",
            )

            toolkit = SQLBotToolkit(
                db=db,
                llm=coder_llm,
                redis_url=str(settings.redis_om_url),
                query_retriever=vector_store.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={
                        "k": 4,
                        "score_threshold": 0.2,
                        "filter": RedisText("type") == "query",
                    },
                ),
                relationship_retriever=vector_store.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={
                        "k": 4,
                        "score_threshold": 0.2,
                        "filter": RedisText("type") == "relationship",
                    },
                ),
                conversation_id=message.conversation,
            )

            history = AppendSuffixHistory(
                url=str(settings.redis_om_url),
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

            def _should_persist(tags: list) -> bool:
                # Only require approval on sql_db_query.
                return tags is not None and "agent_executor_chain" in tags

            history_callback = PersistHistoryCallbackHandler(
                memory=memory, should_persist=_should_persist
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
