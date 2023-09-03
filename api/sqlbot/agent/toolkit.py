"""Toolkit for interacting with a SQL database."""

from fastapi import WebSocket
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool
from langchain.tools.sql_database.tool import QuerySQLCheckerTool
from pydantic import RedisDsn

from sqlbot.callbacks import WebsocketHumanApprovalCallbackHandler
from sqlbot.tools import (
    FakeAsyncTableSchemaTool,
    CustomListTablesTool,
    FakeAsyncQuerySQLDataBaseTool,
)


class SQLBotToolkit(SQLDatabaseToolkit):
    redis_url: RedisDsn = "redis://localhost:6379"
    websocket: WebSocket
    conversation_id: str

    def get_tools(self) -> list[BaseTool]:
        """Get the tools in the toolkit."""
        list_tables_tool = CustomListTablesTool(db=self.db, redis_url=self.redis_url)
        table_schema_tool_description = (
            "Use this tool to get the schema of specific tables. "
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. "
            "Be sure that the tables actually exist by calling "
            f"{list_tables_tool.name} first! "
            "Example Input: 'table1, table2, table3'"
        )
        table_schema_tool = FakeAsyncTableSchemaTool(
            db=self.db, description=table_schema_tool_description
        )
        query_sql_database_tool_description = (
            "Use this tool to execute query and get result from the database. "
            "Input to this tool is a SQL query, output is a result from the database. "
            "If the query is not correct, an error message will be returned. "
            "If an error is returned, rewrite the query and try again. "
            "If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', or no such column 'xxxx', use {table_schema_tool.name} "
            "to get the correct table columns."
        )

        def _should_check(serialized_obj: dict) -> bool:
            # Only require approval on sql_db_query.
            return serialized_obj.get("name") == "sql_db_query"

        human_approval_callback_handler = WebsocketHumanApprovalCallbackHandler(
            self.websocket, self.conversation_id, should_check=_should_check
        )
        query_sql_database_tool = FakeAsyncQuerySQLDataBaseTool(
            db=self.db,
            description=query_sql_database_tool_description,
            callbacks=[human_approval_callback_handler],
        )
        query_sql_checker_tool_description = (
            "Use this tool to check if your query is correct before executing "
            "it. Always use this tool before executing a query with "
            f"{query_sql_database_tool.name}!"
        )
        query_sql_checker_tool = QuerySQLCheckerTool(
            db=self.db, llm=self.llm, description=query_sql_checker_tool_description
        )
        return [
            query_sql_database_tool,
            table_schema_tool,
            list_tables_tool,
            query_sql_checker_tool,
        ]
