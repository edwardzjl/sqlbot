from langchain.embeddings import HuggingFaceEmbeddings, HuggingFaceInstructEmbeddings
from langchain.schema import Document
from langchain.utilities.sql_database import SQLDatabase
from langchain.vectorstores.redis import Redis


model_name = "intfloat/multilingual-e5-large"
model_kwargs = {"device": "cpu"}
encode_kwargs = {"normalize_embeddings": True}
embeddings = HuggingFaceInstructEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,
)


def store_vector_store_sql(
    chat_id: str,
    user_id: str,
    query_payload: dict,
    relationship_payload: dict,
):
    query_docs = [
        Document(
            page_content=question,
            metadata={"sql_query": query_payload[question], "type": "query"},
        )
        for question in query_payload.keys()
    ]
    rds = Redis.from_documents(
        documents=query_docs,
        embedding=embeddings,
        redis_url="redis://127.0.0.1:6379/0",
        index_name=f"{user_id}:{chat_id}",
    )
    relationship_docs = [
        Document(
            page_content=question,
            metadata={
                "sql_query": relationship_payload[question],
                "type": "relationship",
            },
        )
        for question in relationship_payload.keys()
    ]
    rds = Redis.from_documents(
        documents=relationship_docs,
        embedding=embeddings,
        redis_url="redis://127.0.0.1:6379/0",
        index_name=f"{user_id}:{chat_id}",
    )
    rds.write_schema("redis_schema.yaml")


def append_vector_store_sql(
    chat_id: str,
    user_id: str,
    payload: dict,
):
    vector_store = Redis.from_existing_index(
        redis_url="redis://localhost:6379/0",
        embedding=embeddings,
        index_name=f"{user_id}:{chat_id}",
        schema="redis_schema.yaml",
    )
    docs = [
        Document(
            page_content=question,
            metadata={"sql_query": payload[question], "type": payload["type"]},
        )
        for question in payload.keys()
    ]
    vector_store.add_documents(documents=docs)
