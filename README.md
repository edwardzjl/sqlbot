# SQLbot

A simple, multi-user, multi-conversation, web-based chatbot to answer questions based on database queries.

This project is evolved from <https://github.com/edwardzjl/chatbot>, utilizing [langchain](https://github.com/langchain-ai/langchain)'s [sql agent](https://python.langchain.com/docs/integrations/toolkits/sql_database) and offers the following features:

- Enhanced Table Descriptions: This feature provides additional table descriptions, empowering Language Model (LLM) to make more informed decisions when selecting target tables.
- Customizable Data Definition Language (DDL, the `CREATE TABLE` statement): Typically, SQL agents are not able to modify the DDL of the database. However, the original DDL often contains extraneous information. Moreover, at least in Postgres, the DDL lacks the column descriptions, which are crucial for LLMs to accurately choose the appropriate columns.
- Redis Integration: Both the supplementary table descriptions and customized DDL are conveniently stored in Redis. This approach ensures swift access and facilitates straightforward updates.

## Demo

A live demo was served at <https://sqlbot.agi.zjuici.com>

This demo was built on [IMDb](https://relational.fit.cvut.cz/dataset/IMDb) dataset, with 6 tables.

## Deployment

See [deployment instructions](./manifests/README.md)

## Configuration

Key | Default Value | Description
---|---|---
LOG_LEVEL | `INFO` | log level
REDIS_OM_URL | `redis://localhost:6379` | Redis url to persist messages and metadata
ISVC_LLM | `http://localhost:8080` | model service url
ISVC_CODER_LLM | `http://localhost:8081` | coder model service url, used for generating and checking SQL queries
WAREHOUSE_URL | `postgresql+psycopg://postgres:postgres@localhost:5432/` | data warehouse url, in which you want to analyze the data
