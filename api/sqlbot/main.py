"""Main entrypoint for the app."""
import json
import time
from contextlib import asynccontextmanager
from typing import Annotated

from aredis_om import Migrator, NotFoundError
from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain.llms.huggingface_text_gen_inference import HuggingFaceTextGenInference
from langchain.sql_database import SQLDatabase
from loguru import logger

from sqlbot.callbacks import TracingLLMCallbackHandler
from sqlbot.config import settings
from sqlbot.routers import router
from sqlbot.state import app_state
from sqlbot.utils import UserIdHeader


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing app state")
    start = time.perf_counter()
    await Migrator().run()
    try:
        with open(settings.custom_table_info, encoding="utf-8") as f:
            custom_table_info: dict = json.load(f)
            tables = custom_table_info.keys()
    except Exception as e:
        logger.warning(
            f"Cannot open custom table info, default to fetching from database. cause: {e}"
        )
        custom_table_info = None
        tables = None
    app_state.warehouse = SQLDatabase.from_uri(
        str(settings.warehouse_url),
        custom_table_info=custom_table_info,
        include_tables=tables,
        sample_rows_in_table_info=3,
    )
    tracing_callback = TracingLLMCallbackHandler()
    app_state.llm = HuggingFaceTextGenInference(
        inference_server_url=str(settings.isvc_llm),
        max_new_tokens=512,
        temperature=0.8,
        top_p=0.8,
        stop_sequences=["<|im_end|>"],
        streaming=True,
        callbacks=[tracing_callback],
    )
    app_state.coder_llm = HuggingFaceTextGenInference(
        inference_server_url=str(settings.isvc_llm),
        max_new_tokens=512,
        temperature=0.8,
        top_p=0.8,
        stop_sequences=["<|im_end|>"],
    )
    end = time.perf_counter()
    logger.info(f"App initialized in {(end - start):.4}s")
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


@app.get("/api/healthz")
def healthz():
    return "OK"


@app.get("/api/userinfo")
def userinfo(userid: Annotated[str | None, UserIdHeader()] = None):
    return {"username": userid}


@app.exception_handler(NotFoundError)
async def notfound_exception_handler(request: Request, exc: NotFoundError):
    logger.error(f"NotFoundError: {exc}")
    # TODO: add some details here
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"detail": str(exc)}),
    )


app.mount(
    "/", StaticFiles(directory="static", html=True, check_dir=False), name="static"
)
